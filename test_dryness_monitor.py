import unittest
import random
from dryness_monitor import DrynessMonitor

class TestDrynessMonitor(unittest.TestCase):
    def test_initial_state(self):
        monitor = DrynessMonitor()
        self.assertFalse(monitor.is_dry(), "Should not be dry initially without data")

    def test_wet_state(self):
        # Wet state: Both T and P rise (simulating heating water in closed vessel)
        monitor = DrynessMonitor(min_temp_rate=0.5, max_pressure_rate=0.1)

        for i in range(10):
            monitor.add_reading(temperature=100 + i*1.0, pressure=10 + i*0.5, timestamp=i*1.0)

        self.assertFalse(monitor.is_dry(), "Should not be dry when pressure is rising significantly")

    def test_dry_state(self):
        # Dry state: T rises, P stays relatively constant
        monitor = DrynessMonitor(min_temp_rate=0.5, max_pressure_rate=0.1)

        for i in range(10):
            monitor.add_reading(temperature=150 + i*1.0, pressure=20 + i*0.05, timestamp=i*1.0)

        self.assertTrue(monitor.is_dry(), "Should be dry when temp rises and pressure is stable")

    def test_cooling_or_steady_temp(self):
        # Temp not rising enough or cooling
        monitor = DrynessMonitor(min_temp_rate=0.5, max_pressure_rate=0.1)

        for i in range(10):
            monitor.add_reading(temperature=100 - i*1.0, pressure=10, timestamp=i*1.0)

        self.assertFalse(monitor.is_dry(), "Should not be dry if temp is cooling")

        monitor = DrynessMonitor(min_temp_rate=0.5, max_pressure_rate=0.1)

        for i in range(10):
            monitor.add_reading(temperature=100 + i*0.1, pressure=10, timestamp=i*1.0)

        self.assertFalse(monitor.is_dry(), "Should not be dry if temp is not rising fast enough")

    def test_pressure_drop(self):
        # Pressure dropping while temp rises
        monitor = DrynessMonitor(min_temp_rate=0.5, max_pressure_rate=0.1)

        for i in range(10):
            monitor.add_reading(temperature=100 + i*1.0, pressure=10 - i*0.1, timestamp=i*1.0)

        self.assertTrue(monitor.is_dry(), "Should be dry if pressure is dropping while temp rises")

    def test_zero_time_diff(self):
        monitor = DrynessMonitor(min_temp_rate=0.5, max_pressure_rate=0.1)

        for i in range(5):
            monitor.add_reading(temperature=100 + i, pressure=10, timestamp=1.0)

        self.assertFalse(monitor.is_dry(), "Should handle 0 time difference safely by returning False")

    def test_noisy_high_frequency_data(self):
        # Simulating noisy sensor data smoothed by EMA filtering
        monitor = DrynessMonitor(min_temp_rate=0.5, max_pressure_rate=0.1, history_len=30, ema_alpha=0.1)

        random.seed(42)

        # Temp rises at 1.0 deg/sec on average (+ noise)
        # Pressure is stable (+ noise)
        for i in range(100):
            t = i * 0.1  # 100ms intervals over 10s
            temp = 100 + (t * 1.0) + (random.random() - 0.5) * 2.0
            pressure = 10 + (random.random() - 0.5) * 1.0
            monitor.add_reading(temperature=temp, pressure=pressure, timestamp=t)

        self.assertTrue(monitor.is_dry(), "EMA filter should smooth high-frequency noise and accurately detect dry state")

    def test_low_moisture_sample(self):
        # Low moisture sample (e.g. bread charring): dT/dt rises rapidly, dP/dt remains flat near zero
        monitor = DrynessMonitor(min_temp_rate=0.5, max_pressure_rate=0.1, history_len=15, ema_alpha=0.2)

        for i in range(20):
            t = i * 0.5
            temp = 110 + (t * 1.5)  # rapid temperature slope
            pressure = 0.2 + (t * 0.005)  # negligible pressure change
            monitor.add_reading(temperature=temp, pressure=pressure, timestamp=t)

        self.assertTrue(monitor.is_dry(), "Should correctly detect dry state for low-moisture samples with rapid dT/dt and flat dP/dt")

if __name__ == '__main__':
    unittest.main()
