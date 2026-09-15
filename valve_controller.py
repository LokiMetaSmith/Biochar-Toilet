import math
import time

class ValveController:
    """
    Controls the steam valve for the Biochar Toilet reaction vessel with safety interlocks.
    Uses time-proportional control (PWM simulation) for logarithmic pressure release.
    """
    def __init__(self, target_pressure=15.0, target_temperature=121.0, min_seal_pressure=4.0, max_safe_pressure=18.0, max_safe_temperature=250.0, window_ms=2000, start_time_ms=None):
        """
        Initializes the ValveController.

        Args:
            target_pressure (float): Maximum target pressure before safety limits.
            target_temperature (float): Target temperature to trigger release.
            min_seal_pressure (float): Hard floor to preserve seal integrity (default 4.0 PSI).
            max_safe_pressure (float): Emergency overpressure limit (default 18.0 PSI).
            max_safe_temperature (float): Emergency overtemperature limit (default 250.0 C).
            window_ms (int): The duration of the PWM simulation window in milliseconds.
            start_time_ms (float): Optional starting time for deterministic testing.
        """
        self.target_pressure = target_pressure
        self.target_temperature = target_temperature
        self.min_seal_pressure = min_seal_pressure
        self.max_safe_pressure = max_safe_pressure
        self.max_safe_temperature = max_safe_temperature

        self.valve_open = False
        self.release_active = False
        self.emergency_tripped = False

        self.window_ms = window_ms
        self.window_start = start_time_ms if start_time_ms is not None else time.time() * 1000

    def get_time_ms(self):
        return time.time() * 1000

    def update(self, pressure, temperature, current_time_ms=None):
        """
        Updates the valve state based on current sensor readings and safety checks.

        Args:
            pressure (float): Current pressure reading.
            temperature (float): Current temperature reading.
            current_time_ms (float): Optional timestamp in ms for deterministic testing.
        """
        if current_time_ms is None:
            current_time_ms = self.get_time_ms()

        # Emergency Interlock Check
        if pressure >= self.max_safe_pressure or temperature >= self.max_safe_temperature:
            self.emergency_tripped = True
            self.valve_open = True
            return

        if self.emergency_tripped:
            self.valve_open = True
            self.release_active = False
            return

        if not self.release_active and pressure >= self.target_pressure and temperature >= self.target_temperature:
            self.release_active = True

        if self.release_active:
            # CRITICAL SAFETY FLOOR: Close valve instantly if pressure hits or drops below the minimum threshold
            if pressure <= self.min_seal_pressure:
                self.valve_open = False
                self.release_active = False
            else:
                # Calculate duty cycle logarithmically based on pressure difference
                # Higher pressure -> larger t -> higher duty cycle
                # Lower pressure -> smaller t -> lower duty cycle
                clamped_pressure = min(pressure, self.target_pressure)
                range_p = self.target_pressure - self.min_seal_pressure

                if range_p <= 0:
                    duty_cycle = 0.0
                else:
                    t = (clamped_pressure - self.min_seal_pressure) / range_p
                    log_factor = math.log1p(t * 1.71828) / 1.0
                    duty_cycle = max(0.0, min(1.0, log_factor))

                # Time-proportional PWM simulation
                if (current_time_ms - self.window_start) >= self.window_ms:
                    self.window_start = current_time_ms

                # The valve is open for the first 'duty_cycle * window_ms' portion of the window
                self.valve_open = (current_time_ms - self.window_start) < (duty_cycle * self.window_ms)
        else:
            self.valve_open = False

    def is_open(self):
        """Returns True if the valve is open."""
        return self.valve_open

    def is_emergency_tripped(self):
        """Returns True if an emergency safety trip has occurred."""
        return self.emergency_tripped

    def reset(self, current_time_ms=None):
        """Resets the valve and clears emergency trip state."""
        self.valve_open = False
        self.release_active = False
        self.emergency_tripped = False
        if current_time_ms is None:
            current_time_ms = self.get_time_ms()
        self.window_start = current_time_ms
