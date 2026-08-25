"""
test_dryness_monitor.py — Comprehensive Unit Test Suite for DrynessMonitor

Tests the thermodynamic dryness detection algorithm under various operational conditions:
  - Initial uninitialized state handling.
  - Wet state (phase change / steam expansion with rising pressure).
  - Normal dry state (sensible heating with stable pressure).
  - Cooling or insufficient temperature rise scenarios.
  - Pressure drop scenarios (venting / vacuum swing / leak).
  - Zero time-difference edge cases (batch updates / duplicate timestamps).
  - High-frequency noisy sensor data smoothed via Exponential Moving Average (EMA).
  - Low-moisture samples (e.g., bread charring) featuring rapid dT/dt and flat dP/dt.
"""

import unittest
import random
from dryness_monitor import DrynessMonitor

class TestDrynessMonitor(unittest.TestCase):
    """Unit test suite for verifying DrynessMonitor rate calculations and filtering."""

    def test_initial_state(self):
        """Verify that the monitor defaults to False when no readings have been recorded."""
        monitor = DrynessMonitor()
        self.assertFalse(monitor.is_dry(), "Should not be dry initially without data")

    def test_wet_state(self):
        """
        Verify wet state detection.
        Simulates heating liquid water in a sealed vessel where both temperature and
        pressure rise concurrently due to steam generation (dP/dt > max_pressure_rate).
        """
        monitor = DrynessMonitor(min_temp_rate=0.5, max_pressure_rate=0.1)

        for i in range(10):
            monitor.add_reading(temperature=100 + i * 1.0, pressure=10 + i * 0.5, timestamp=i * 1.0)

        self.assertFalse(monitor.is_dry(), "Should not be dry when pressure is rising significantly")

    def test_dry_state(self):
        """
        Verify normal dry state detection.
        Simulates post-evaporation sensible heating where temperature continues to rise
        rapidly (dT/dt > min_temp_rate) while pressure remains stable (dP/dt < max_pressure_rate).
        """
        monitor = DrynessMonitor(min_temp_rate=0.5, max_pressure_rate=0.1)

        for i in range(10):
            monitor.add_reading(temperature=150 + i * 1.0, pressure=20 + i * 0.05, timestamp=i * 1.0)

        self.assertTrue(monitor.is_dry(), "Should be dry when temp rises and pressure is stable")

    def test_cooling_or_steady_temp(self):
        """
        Verify that cooling or slow temperature rise does NOT trigger a false positive dry state,
        even if pressure is completely stable.
        """
        monitor = DrynessMonitor(min_temp_rate=0.5, max_pressure_rate=0.1)

        # Cooling scenario (dT/dt < 0)
        for i in range(10):
            monitor.add_reading(temperature=100 - i * 1.0, pressure=10, timestamp=i * 1.0)

        self.assertFalse(monitor.is_dry(), "Should not be dry if temp is cooling")

        # Insufficient temp rise scenario (dT/dt below min_temp_rate)
        monitor = DrynessMonitor(min_temp_rate=0.5, max_pressure_rate=0.1)

        for i in range(10):
            monitor.add_reading(temperature=100 + i * 0.1, pressure=10, timestamp=i * 1.0)

        self.assertFalse(monitor.is_dry(), "Should not be dry if temp is not rising fast enough")

    def test_pressure_drop(self):
        """
        Verify dry state detection when pressure drops (e.g., during valve venting or vacuum swing).
        Negative dP/dt combined with positive dT/dt satisfies the dryness criterion.
        """
        monitor = DrynessMonitor(min_temp_rate=0.5, max_pressure_rate=0.1)

        for i in range(10):
            monitor.add_reading(temperature=100 + i * 1.0, pressure=10 - i * 0.1, timestamp=i * 1.0)

        self.assertTrue(monitor.is_dry(), "Should be dry if pressure is dropping while temp rises")

    def test_zero_time_diff(self):
        """
        Verify robust handling of zero time difference (duplicate timestamps / fast polling).
        Ensures division by zero is safely avoided and returns False.
        """
        monitor = DrynessMonitor(min_temp_rate=0.5, max_pressure_rate=0.1)

        for i in range(5):
            monitor.add_reading(temperature=100 + i, pressure=10, timestamp=1.0)

        self.assertFalse(monitor.is_dry(), "Should handle 0 time difference safely by returning False")

    def test_noisy_high_frequency_data(self):
        """
        Verify Exponential Moving Average (EMA) noise suppression on high-frequency sensor streams.
        Simulates 100Hz ADC noise overlaid on temperature and pressure signals.
        """
        monitor = DrynessMonitor(min_temp_rate=0.5, max_pressure_rate=0.1, history_len=30, ema_alpha=0.1)

        random.seed(42)

        for i in range(100):
            t = i * 0.1  # 100ms sample interval
            temp = 100 + (t * 1.0) + (random.random() - 0.5) * 2.0  # signal + noise
            pressure = 10 + (random.random() - 0.5) * 1.0          # noise around flat baseline
            monitor.add_reading(temperature=temp, pressure=pressure, timestamp=t)

        self.assertTrue(monitor.is_dry(), "EMA filter should smooth high-frequency noise and accurately detect dry state")

    def test_low_moisture_sample(self):
        """
        Verify dryness detection for low-moisture samples (e.g., pre-dried biomass or bread charring).
        For low-moisture samples, steam generation is negligible (dP/dt ≈ 0), but energy input causes
        a steep temperature slope (dT/dt >> min_temp_rate).
        """
        monitor = DrynessMonitor(min_temp_rate=0.5, max_pressure_rate=0.1, history_len=15, ema_alpha=0.2)

        for i in range(20):
            t = i * 0.5
            temp = 110 + (t * 1.5)        # steep temperature slope
            pressure = 0.2 + (t * 0.005)   # flat pressure baseline
            monitor.add_reading(temperature=temp, pressure=pressure, timestamp=t)

        self.assertTrue(monitor.is_dry(), "Should correctly detect dry state for low-moisture samples with rapid dT/dt and flat dP/dt")

if __name__ == '__main__':
    unittest.main()
