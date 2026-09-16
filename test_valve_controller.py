"""
test_valve_controller.py — Unit tests for ValveController logic and emergency safety interlocks.
"""

import unittest
from valve_controller import ValveController

class TestValveController(unittest.TestCase):
    def test_initial_state(self):
        controller = ValveController(start_time_ms=0)
        self.assertFalse(controller.is_open())
        self.assertFalse(controller.is_emergency_tripped())

    def test_minimum_seal_pressure_floor(self):
        controller = ValveController(target_pressure=8.0, target_temperature=121.0, min_seal_pressure=4.0, max_safe_pressure=18.0, max_safe_temperature=250.0, start_time_ms=0)

        # Trigger release cycle first
        controller.update(pressure=8.0, temperature=121.0, current_time_ms=0)

        # Pressure drops to 4.0 PSI floor, valve should close and release should end
        controller.update(pressure=4.0, temperature=121.0, current_time_ms=500)
        self.assertFalse(controller.is_open())
        self.assertFalse(controller.release_active)

    def test_time_proportional_logarithmic_control(self):
        # Window is 2000ms
        controller = ValveController(target_pressure=8.0, target_temperature=121.0, min_seal_pressure=4.0, max_safe_pressure=18.0, max_safe_temperature=250.0, window_ms=2000, start_time_ms=0)

        # Trigger release cycle
        controller.update(pressure=8.0, temperature=121.0, current_time_ms=0)

        # Let's test at pressure = 8.0 (High pressure).
        # t = (8.0 - 4.0) / 4.0 = 1.0
        # duty = log1p(1.0 * 1.71828) = log1p(1.71828) = 1.0 -> Valve should be OPEN entirely
        controller.update(pressure=8.0, temperature=121.0, current_time_ms=100)
        self.assertTrue(controller.is_open())

        # Let's test at pressure = 4.1 (Low pressure, just above floor).
        # t = (4.1 - 4.0) / 4.0 ~= 0.025
        # duty = log1p(0.025 * 1.71828) ~= 0.042 -> Valve should be barely OPEN
        controller.update(pressure=4.1, temperature=121.0, current_time_ms=0) # New window
        self.assertTrue(controller.is_open()) # Open at the very beginning of the window

        controller.update(pressure=4.1, temperature=121.0, current_time_ms=1000)
        self.assertFalse(controller.is_open()) # Halfway through window, duty cycle is small, so closed

    def test_emergency_overpressure_trip(self):
        controller = ValveController(target_pressure=8.0, min_seal_pressure=4.0, max_safe_pressure=18.0, max_safe_temperature=250.0, start_time_ms=0)

        # Pressure exceeds emergency safe limit (18.0 PSI)
        controller.update(pressure=18.5, temperature=80.0, current_time_ms=0)
        self.assertTrue(controller.is_open(), "Valve should open immediately during emergency overpressure")
        self.assertTrue(controller.is_emergency_tripped(), "Controller should register emergency trip state")

    def test_emergency_overtemp_trip(self):
        controller = ValveController(target_pressure=8.0, min_seal_pressure=4.0, max_safe_pressure=18.0, max_safe_temperature=250.0, start_time_ms=0)

        # Temperature exceeds emergency safe limit (250.0 °C)
        controller.update(pressure=10.0, temperature=255.0, current_time_ms=0)
        self.assertTrue(controller.is_open(), "Valve should open immediately during emergency overtemp")
        self.assertTrue(controller.is_emergency_tripped(), "Controller should register emergency trip state")

    def test_emergency_latching_behavior(self):
        controller = ValveController(target_pressure=8.0, target_temperature=121.0, min_seal_pressure=4.0, max_safe_pressure=18.0, max_safe_temperature=250.0, start_time_ms=0)

        # Trip emergency
        controller.update(pressure=19.0, temperature=121.0, current_time_ms=0)
        self.assertTrue(controller.is_open())

        # Pressure drops after emergency trip, valve should stay latched open
        controller.update(pressure=3.0, temperature=100.0, current_time_ms=100)
        self.assertTrue(controller.is_open())

    def test_normal_release_behavior(self):
        controller = ValveController(target_pressure=8.0, target_temperature=121.0, min_seal_pressure=4.0, max_safe_pressure=18.0, max_safe_temperature=250.0, start_time_ms=0)

        # Pressure hasn't reached target yet
        controller.update(pressure=7.0, temperature=121.0, current_time_ms=0)
        self.assertFalse(controller.is_open())
        self.assertFalse(controller.release_active)

        # Target hit! Release triggers.
        controller.update(pressure=8.0, temperature=121.0, current_time_ms=0)
        self.assertTrue(controller.release_active)

        # Even if temp drops, release continues until pressure floor is hit
        controller.update(pressure=10.0, temperature=100.0, current_time_ms=0)
        self.assertTrue(controller.release_active)

        # Hit floor, release ends
        controller.update(pressure=4.0, temperature=100.0, current_time_ms=0)
        self.assertFalse(controller.is_open())
        self.assertFalse(controller.release_active)

    def test_reset(self):
        controller = ValveController(start_time_ms=0)
        controller.update(pressure=19.0, temperature=255.0, current_time_ms=0)
        self.assertTrue(controller.is_open())
        controller.reset(current_time_ms=100)
        self.assertFalse(controller.is_open())
        self.assertFalse(controller.is_emergency_tripped())

if __name__ == '__main__':
    unittest.main()
