import time

class HeaterController:
    """
    Controls a heating element (resistive or induction SSR driver) for bio-char production.

    Provides temperature regulation using Proportional (P) control with a hysteresis band,
    time-window PWM duty cycle calculation, dry protection interlocks, and over-temperature safety cutoffs.
    """

    def __init__(self, target_setpoint=200.0, hysteresis=2.0, kp=0.03, window_ms=2000, max_safe_temp=250.0):
        """
        Initializes the HeaterController.

        Args:
            target_setpoint (float): Target operational temperature in °C (default 200.0 °C).
            hysteresis (float): Hysteresis band above setpoint to force duty to 0% in °C (default 2.0 °C).
            kp (float): Proportional gain for duty cycle calculation (default 0.03).
            window_ms (int): PWM window period in milliseconds (default 2000 ms).
            max_safe_temp (float): Hard upper thermal limit for safety shutoff in °C (default 250.0 °C).
        """
        self.target_setpoint = target_setpoint
        self.hysteresis = hysteresis
        self.kp = kp
        self.window_ms = window_ms
        self.max_safe_temp = max_safe_temp

        self.heater_on = False
        self.duty_cycle = 0.0
        self.overtemp_tripped = False
        self.dry_latched = False
        self.window_start_ms = 0

    def compute_duty_cycle(self, current_temp):
        """
        Computes the proportional PWM duty cycle (0.0 to 1.0) given current temperature.

        Args:
            current_temp (float): Current temperature reading in °C.

        Returns:
            float: Calculated duty cycle between 0.0 (0%) and 1.0 (100%).
        """
        if current_temp >= (self.target_setpoint + self.hysteresis):
            return 0.0

        error = self.target_setpoint - current_temp
        duty = self.kp * error

        if duty < 0.0:
            duty = 0.0
        elif duty > 1.0:
            duty = 1.0

        return duty

    def update(self, current_temp, now_ms=None, dry_latched=False):
        """
        Updates the heater state based on current temperature, time window, and safety inputs.

        Args:
            current_temp (float): Current temperature in °C.
            now_ms (int, optional): Current timestamp in milliseconds. Defaults to current system time.
            dry_latched (bool): Interlock signal indicating dry boiler protection latched.

        Returns:
            bool: True if heater output should be active, False otherwise.
        """
        if now_ms is None:
            now_ms = int(time.time() * 1000)

        self.dry_latched = dry_latched

        # Safety Check: Hard Overtemperature Trip
        if current_temp >= self.max_safe_temp:
            self.overtemp_tripped = True

        if self.overtemp_tripped or self.dry_latched:
            self.duty_cycle = 0.0
            self.heater_on = False
            return False

        # Calculate Duty Cycle
        self.duty_cycle = self.compute_duty_cycle(current_temp)

        # Time Window PWM Calculation
        if self.window_start_ms == 0 or (now_ms - self.window_start_ms) >= self.window_ms:
            self.window_start_ms = now_ms

        elapsed = now_ms - self.window_start_ms
        active_duration = int(self.duty_cycle * self.window_ms)

        self.heater_on = elapsed < active_duration
        return self.heater_on

    def is_on(self):
        """Returns True if the heater output is active."""
        return self.heater_on

    def is_overtemp_tripped(self):
        """Returns True if an over-temperature safety trip has occurred."""
        return self.overtemp_tripped

    def reset(self):
        """Resets the controller and clears safety trip states."""
        self.heater_on = False
        self.duty_cycle = 0.0
        self.overtemp_tripped = False
        self.dry_latched = False
        self.window_start_ms = 0
