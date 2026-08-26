import collections

class DrynessMonitor:
    def __init__(self, min_temp_rate=0.5, max_pressure_rate=0.1, history_len=10, ema_alpha=0.2):
        """
        Initializes the DrynessMonitor with Exponential Moving Average (EMA) filtering
        and dual-criterion dryness detection for noisy and low-moisture samples.

        Args:
            min_temp_rate (float): Minimum rate of temperature rise (deg/sec) to consider as heating up.
            max_pressure_rate (float): Maximum rate of pressure rise (unit/sec) to consider as "not rising" (i.e. dry).
            history_len (int): Number of past readings to keep in the rolling buffer for rate calculation.
            ema_alpha (float): Smoothing factor for EMA filtering (0 < alpha <= 1.0). Lower values offer stronger noise suppression.
        """
        self.min_temp_rate = min_temp_rate
        self.max_pressure_rate = max_pressure_rate
        self.history_len = history_len
        self.ema_alpha = ema_alpha
        self.history = collections.deque(maxlen=history_len)

        self.filtered_temp = None
        self.filtered_pressure = None

    def add_reading(self, temperature, pressure, timestamp):
        """
        Adds a new reading to the monitor, applying EMA noise filtering.

        Args:
            temperature (float): Current raw temperature reading.
            pressure (float): Current raw pressure reading.
            timestamp (float): Current timestamp (in seconds).
        """
        if self.filtered_temp is None:
            self.filtered_temp = float(temperature)
            self.filtered_pressure = float(pressure)
        else:
            self.filtered_temp = self.ema_alpha * float(temperature) + (1.0 - self.ema_alpha) * self.filtered_temp
            self.filtered_pressure = self.ema_alpha * float(pressure) + (1.0 - self.ema_alpha) * self.filtered_pressure

        # Storing filtered tuple: (filtered_temp, filtered_pressure, timestamp)
        self.history.append((self.filtered_temp, self.filtered_pressure, float(timestamp)))

    def is_dry(self):
        """
        Determines if the sample is dry based on the filtered history of readings.

        Condition:
          Temperature slope dT/dt > min_temp_rate AND
          Pressure slope dP/dt < max_pressure_rate.

        Returns:
            bool: True if the sample is considered dry, False otherwise.
        """
        if len(self.history) < 2:
            return False

        # Calculate rates using the first and last filtered points in the history window
        start_temp, start_pressure, start_time = self.history[0]
        end_temp, end_pressure, end_time = self.history[-1]

        time_diff = end_time - start_time

        if time_diff <= 0:
            return False

        temp_rate = (end_temp - start_temp) / time_diff
        pressure_rate = (end_pressure - start_pressure) / time_diff

        return temp_rate > self.min_temp_rate and pressure_rate < self.max_pressure_rate
