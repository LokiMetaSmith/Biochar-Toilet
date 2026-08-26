class ValveController:
    """
    Controls the steam valve for the Biochar Toilet reaction vessel with safety interlocks.

    The valve is initially closed. When the pressure reaches the target (e.g., 15 PSI)
    and the temperature reaches the target (e.g., 121 C), the valve opens to "flash"
    the steam, sterilizing and destroying the sample.

    Safety interlocks will trigger an emergency open state if maximum safe pressure
    or maximum safe temperature limits are exceeded.
    """
    def __init__(self, target_pressure=15.0, target_temperature=121.0, max_safe_pressure=18.0, max_safe_temperature=250.0):
        """
        Initializes the ValveController.

        Args:
            target_pressure (float): Operational pressure threshold to trigger opening (default 15.0 PSI).
            target_temperature (float): Operational temperature threshold to trigger opening (default 121.0 C).
            max_safe_pressure (float): Emergency overpressure limit (default 18.0 PSI).
            max_safe_temperature (float): Emergency overtemperature limit (default 250.0 C).
        """
        self.target_pressure = target_pressure
        self.target_temperature = target_temperature
        self.max_safe_pressure = max_safe_pressure
        self.max_safe_temperature = max_safe_temperature
        self.valve_open = False
        self.emergency_tripped = False

    def update(self, pressure, temperature):
        """
        Updates the valve state based on current sensor readings and safety checks.

        Args:
            pressure (float): Current pressure reading.
            temperature (float): Current temperature reading.
        """
        # Emergency Interlock Check
        if pressure >= self.max_safe_pressure or temperature >= self.max_safe_temperature:
            self.emergency_tripped = True
            self.valve_open = True
            return

        # Operational Threshold Check
        if not self.valve_open and not self.emergency_tripped:
            if pressure >= self.target_pressure and temperature >= self.target_temperature:
                self.valve_open = True

    def is_open(self):
        """Returns True if the valve is open."""
        return self.valve_open

    def is_emergency_tripped(self):
        """Returns True if an emergency safety trip has occurred."""
        return self.emergency_tripped

    def reset(self):
        """Resets the valve and clears emergency trip state."""
        self.valve_open = False
        self.emergency_tripped = False
