"""
cycle_orchestrator.py — High-Level Operational Lifecycle Orchestrator for Biochar Production.

Orchestrates HeaterController, ValveController, and DrynessMonitor into a unified state machine:
  - IDLE / OFF: Standby waiting for cycle start.
  - HEATING / DRYING: Boiling and drying sample with active pressure swing regulation.
  - CHARRING: High-temperature pyrolysis phase once dryness is detected.
  - COOLING: Controlled cool-down after charring completion.
  - ERROR: Latched fault state with valve vented and heaters disabled.

Safety Interlocks (mirroring ESP32 C firmware specifications):
  - Emergency overpressure trip (latches ERROR, vents valve, shuts off heaters).
  - Emergency overtemperature trip (latches ERROR, vents valve, shuts off heaters).
  - Negative pressure fault trip (e.g. sensor failure or excessive vacuum).
  - Thermal runaway in OFF/COOLING (absolute +50°C jump or +5°C rise after 1-hour grace period).
  - Thermal stagnation during HEATING (<3.0°C rise over a rolling 1-hour window).
"""

from enum import Enum
import collections
import time
from heater_controller import HeaterController
from valve_controller import ValveController
from dryness_monitor import DrynessMonitor


class CycleState(Enum):
    IDLE = "IDLE"
    HEATING = "HEATING"
    CHARRING = "CHARRING"
    COOLING = "COOLING"
    ERROR = "ERROR"


class CycleOrchestrator:
    def __init__(
        self,
        heater_controller=None,
        valve_controller=None,
        dryness_monitor=None,
        drying_temp_setpoint=130.0,
        charring_temp_setpoint=220.0,
        charring_duration_ms=600000,   # 10 minutes default charring dwell
        cooling_safe_temp=60.0,        # Safe opening/idle threshold
        stagnation_window_ms=3600000,  # 1 hour
        stagnation_min_rise_c=3.0,
        runaway_grace_ms=3600000       # 1 hour grace for stuck BJT check
    ):
        self.heater = heater_controller if heater_controller is not None else HeaterController(target_setpoint=drying_temp_setpoint)
        self.valve = valve_controller if valve_controller is not None else ValveController()
        self.dryness = dryness_monitor if dryness_monitor is not None else DrynessMonitor()

        self.drying_temp_setpoint = drying_temp_setpoint
        self.charring_temp_setpoint = charring_temp_setpoint
        self.charring_duration_ms = charring_duration_ms
        self.cooling_safe_temp = cooling_safe_temp
        self.stagnation_window_ms = stagnation_window_ms
        self.stagnation_min_rise_c = stagnation_min_rise_c
        self.runaway_grace_ms = runaway_grace_ms

        self.state = CycleState.IDLE
        self.error_reason = None
        self.cycle_start_time_ms = 0
        self.charring_start_time_ms = 0
        self.cooling_start_time_ms = 0

        # Safety tracking
        self.negative_pressure_count = 0
        self.base_temp_for_absolute_runaway = None
        self.base_temp_for_runaway = None
        self.stagnation_history = collections.deque()  # (timestamp_ms, temp_c)

    def start_cycle(self, current_time_ms=None):
        if self.state == CycleState.ERROR:
            return False

        if current_time_ms is None:
            current_time_ms = int(time.time() * 1000)

        self.state = CycleState.HEATING
        self.cycle_start_time_ms = current_time_ms
        self.stagnation_history.clear()
        self.heater.target_setpoint = self.drying_temp_setpoint
        return True

    def abort_cycle(self, reason="Manual Abort", current_time_ms=None):
        if current_time_ms is None:
            current_time_ms = int(time.time() * 1000)
        self.state = CycleState.COOLING
        self.cooling_start_time_ms = current_time_ms
        self.heater.target_setpoint = 0.0

    def trigger_error(self, reason):
        self.state = CycleState.ERROR
        self.error_reason = reason
        self.valve.emergency_tripped = True
        self.valve.valve_open = True
        self.heater.overtemp_tripped = True
        self.heater.heater_on = False
        self.heater.duty_cycle = 0.0

    def reset_error(self):
        self.state = CycleState.IDLE
        self.error_reason = None
        self.negative_pressure_count = 0
        self.base_temp_for_absolute_runaway = None
        self.base_temp_for_runaway = None
        self.stagnation_history.clear()
        self.valve.reset()
        self.heater.reset()

    def update(self, pressure, temperature, current_time_ms=None):
        if current_time_ms is None:
            current_time_ms = int(time.time() * 1000)

        timestamp_sec = current_time_ms / 1000.0

        # Record sensor reading into DrynessMonitor
        self.dryness.add_reading(temperature, pressure, timestamp_sec)

        # ------------------- SAFETY CHECKS -------------------
        if self.state != CycleState.ERROR:
            # 1. Negative pressure check (e.g., < -0.2 PSI for 3 consecutive checks)
            if pressure < -0.2:
                self.negative_pressure_count += 1
                if self.negative_pressure_count >= 3:
                    self.trigger_error(f"Negative pressure detected ({pressure:.2f} PSI)")
                    return self.state
            else:
                self.negative_pressure_count = 0

            # 2. Overpressure or Overtemperature
            if pressure >= self.valve.max_safe_pressure:
                self.trigger_error(f"Overpressure limit exceeded ({pressure:.2f} PSI)")
                return self.state

            if temperature >= self.heater.max_safe_temp or temperature >= self.valve.max_safe_temperature:
                self.trigger_error(f"Overtemperature limit exceeded ({temperature:.2f} °C)")
                return self.state

            # 3. Thermal Runaway in IDLE/COOLING
            if self.state in (CycleState.IDLE, CycleState.COOLING):
                if self.base_temp_for_absolute_runaway is None:
                    self.base_temp_for_absolute_runaway = temperature
                if self.base_temp_for_runaway is None:
                    self.base_temp_for_runaway = temperature

                # Absolute +50°C runaway
                if (temperature - self.base_temp_for_absolute_runaway) >= 50.0:
                    self.trigger_error(f"Absolute thermal runaway in {self.state.value} (+50C rise)")
                    return self.state
                elif temperature < self.base_temp_for_absolute_runaway:
                    self.base_temp_for_absolute_runaway = temperature

                # +5°C runaway after grace period
                in_grace = False
                if self.cooling_start_time_ms > 0 and (current_time_ms - self.cooling_start_time_ms) <= self.runaway_grace_ms:
                    in_grace = True

                if not in_grace:
                    if (temperature - self.base_temp_for_runaway) >= 5.0:
                        self.trigger_error(f"Stuck heater thermal runaway in {self.state.value} (+5C rise)")
                        return self.state
                    elif temperature < self.base_temp_for_runaway:
                        self.base_temp_for_runaway = temperature

            # 4. Heater Stagnation in HEATING state
            if self.state == CycleState.HEATING:
                self.stagnation_history.append((current_time_ms, temperature))
                # Purge samples older than stagnation window
                while self.stagnation_history and (current_time_ms - self.stagnation_history[0][0]) > self.stagnation_window_ms:
                    self.stagnation_history.popleft()

                if len(self.stagnation_history) > 1:
                    oldest_time, oldest_temp = self.stagnation_history[0]
                    if (current_time_ms - oldest_time) >= (self.stagnation_window_ms - 5000):
                        if (temperature - oldest_temp) < self.stagnation_min_rise_c:
                            self.trigger_error(f"Heater stagnation (temp rise < {self.stagnation_min_rise_c}C over 1 hour)")
                            return self.state

        # If in ERROR state, maintain failsafe states
        if self.state == CycleState.ERROR:
            self.valve.emergency_tripped = True
            self.valve.valve_open = True
            self.heater.overtemp_tripped = True
            self.heater.update(temperature, now_ms=current_time_ms, dry_latched=True)
            return self.state

        # ------------------- STATE MACHINE -------------------
        is_sample_dry = self.valve.dry_latched or self.dryness.is_dry()

        if self.state == CycleState.HEATING:
            # Check if dryness has been detected
            if is_sample_dry:
                self.state = CycleState.CHARRING
                self.charring_start_time_ms = current_time_ms
                self.heater.target_setpoint = self.charring_temp_setpoint

        elif self.state == CycleState.CHARRING:
            if (current_time_ms - self.charring_start_time_ms) >= self.charring_duration_ms:
                self.state = CycleState.COOLING
                self.cooling_start_time_ms = current_time_ms
                self.base_temp_for_runaway = temperature
                self.base_temp_for_absolute_runaway = temperature
                self.heater.target_setpoint = 0.0

        elif self.state == CycleState.COOLING:
            if temperature <= self.cooling_safe_temp:
                self.state = CycleState.IDLE

        # Update subsystem controllers
        dry_flag = (self.state == CycleState.CHARRING or is_sample_dry)
        self.valve.update(pressure, temperature, current_time_ms=current_time_ms)

        # In IDLE and COOLING, heater is kept off
        if self.state in (CycleState.IDLE, CycleState.COOLING):
            self.heater.duty_cycle = 0.0
            self.heater.heater_on = False
        else:
            self.heater.update(temperature, now_ms=current_time_ms, dry_latched=False)

        return self.state
