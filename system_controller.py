from enum import Enum, auto
import collections
import time

class State(Enum):
    OFF = auto()
    HEATING = auto()
    COOLING = auto()
    ERROR = auto()

class SystemController:
    def __init__(self, heater_controller, valve_controller, dryness_monitor=None):
        self.heater = heater_controller
        self.valve = valve_controller
        self.dryness_monitor = dryness_monitor
        self.state = State.OFF

        self.negative_pressure_counter = 0

        # Thermal runaway tracking
        self.cooling_start_time = None
        self.base_temp_for_runaway = None
        self.base_temp_for_absolute_runaway = None

        # Stagnation tracking
        # We need a rolling 180-second window. We'll store tuples of (timestamp, temp)
        self.heating_temp_history = collections.deque()

    def get_time_ms(self):
        return int(time.monotonic() * 1000)

    def transition_to(self, new_state, current_temp=None, current_time_ms=None):
        if self.state == State.ERROR:
            return # Latch in ERROR state

        if current_time_ms is None:
            current_time_ms = self.get_time_ms()

        self.state = new_state

        if new_state == State.COOLING:
            self.cooling_start_time = current_time_ms

        if new_state in (State.OFF, State.COOLING):
            self.base_temp_for_absolute_runaway = current_temp
            self.base_temp_for_runaway = current_temp

        if new_state == State.HEATING:
            self.heating_temp_history.clear()
            if current_temp is not None:
                self.heating_temp_history.append((current_time_ms, current_temp))

        if new_state == State.ERROR:
            self.heater.reset() # Force off
            self.valve.emergency_tripped = True
            self.valve.valve_open = True # Vent

    def update(self, pressure, temperature, current_time_ms=None):
        if current_time_ms is None:
            current_time_ms = self.get_time_ms()

        if self.state == State.ERROR:
            self.heater.duty_cycle = 0.0
            self.heater.heater_on = False
            self.valve.valve_open = True
            return

        # Initialize base temperatures if None (lazy initialization)
        if self.state in (State.OFF, State.COOLING):
            if self.base_temp_for_absolute_runaway is None:
                self.base_temp_for_absolute_runaway = temperature
            if self.base_temp_for_runaway is None:
                self.base_temp_for_runaway = temperature

        # 1. Negative Pressure Failure
        if pressure < -0.2:
            self.negative_pressure_counter += 1
            if self.negative_pressure_counter >= 3: # > 2 consecutive readings
                self.transition_to(State.ERROR)
                return
        else:
            self.negative_pressure_counter = 0

        # 2. Unintended Temperature Rise (Heater Off / Cooling)
        if self.state in (State.OFF, State.COOLING):
            # Absolute 50C rise from when we entered OFF/COOLING
            if self.base_temp_for_absolute_runaway is not None:
                if temperature - self.base_temp_for_absolute_runaway >= 50.0:
                    self.transition_to(State.ERROR)
                    return
                # Update base temp if it drops, so we measure cumulative rise from the lowest point
                if temperature < self.base_temp_for_absolute_runaway:
                    self.base_temp_for_absolute_runaway = temperature

            if self.base_temp_for_runaway is not None:
                grace_period_active = False
                if self.state == State.COOLING and self.cooling_start_time is not None:
                    if current_time_ms - self.cooling_start_time <= 60000:
                        grace_period_active = True

                if not grace_period_active:
                    if temperature - self.base_temp_for_runaway >= 5.0:
                        self.transition_to(State.ERROR)
                        return
                    # Update base temp if it drops
                    if temperature < self.base_temp_for_runaway:
                        self.base_temp_for_runaway = temperature

        # 3. Temperature Stagnation (Heater On)
        if self.state == State.HEATING:
            if not self.heating_temp_history:
                self.heating_temp_history.append((current_time_ms, temperature))
            else:
                self.heating_temp_history.append((current_time_ms, temperature))

            # Remove old entries (> 180 seconds old)
            while self.heating_temp_history and current_time_ms - self.heating_temp_history[0][0] > 180000:
                self.heating_temp_history.popleft()

            # If we have a full 180-second window, check stagnation
            if self.heating_temp_history and current_time_ms - self.heating_temp_history[0][0] >= 179500: # Allow slight tolerance
                oldest_temp = self.heating_temp_history[0][1]
                if temperature - oldest_temp < 3.0:
                    self.transition_to(State.ERROR)
                    return

        # Regular updates
        if self.state == State.HEATING:
            self.heater.update(temperature, current_time_ms)
        else:
            self.heater.duty_cycle = 0.0
            self.heater.heater_on = False

        self.valve.update(pressure, temperature, current_time_ms)

        # Check if valve or heater tripped their own safety
        if self.valve.is_emergency_tripped() or self.heater.is_overtemp_tripped():
            self.transition_to(State.ERROR)

    def get_led_state(self):
        if self.state == State.ERROR:
            return "FLASHING_RED"
        elif self.state == State.HEATING:
            return "SOLID_ORANGE"
        elif self.state == State.COOLING:
            return "SOLID_BLUE"
        else: # OFF
            return "SOLID_GREEN"

    def reset_error(self):
        self.state = State.OFF
        self.heater.reset()
        self.valve.reset()
        self.negative_pressure_counter = 0
        self.base_temp_for_runaway = None
        self.base_temp_for_absolute_runaway = None
        self.cooling_start_time = None
        self.heating_temp_history.clear()
