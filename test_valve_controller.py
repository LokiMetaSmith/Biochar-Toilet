"""
test_valve_controller.py — Unit tests for ValveController logic and emergency safety interlocks.
"""

import unittest
from valve_controller import ValveController

class TestValveController(unittest.TestCase):
    def test_initial_state(self):
        controller = ValveController()
        self.assertFalse(controller.is_open())
        self.assertFalse(controller.is_emergency_tripped())

    def test_heating_phase(self):
        controller = ValveController(target_pressure=15.0, target_temperature=121.0, max_safe_pressure=18.0, max_safe_temperature=250.0)
        # Pressure and Temp below target
        controller.update(pressure=10.0, temperature=100.0)
        self.assertFalse(controller.is_open())

        # Pressure high, Temp low
        controller.update(pressure=16.0, temperature=100.0)
        self.assertFalse(controller.is_open())

        # Pressure low, Temp high
        controller.update(pressure=10.0, temperature=125.0)
        self.assertFalse(controller.is_open())

    def test_threshold_crossing(self):
        controller = ValveController(target_pressure=15.0, target_temperature=121.0, max_safe_pressure=18.0, max_safe_temperature=250.0)

        # Start below threshold
        controller.update(pressure=14.0, temperature=120.0)
        self.assertFalse(controller.is_open())

        # Transition to exactly threshold
        controller.update(pressure=15.0, temperature=121.0)
        self.assertTrue(controller.is_open())

        # Reset and test crossing from below to strictly above
        controller.reset()
        controller.update(pressure=14.9, temperature=120.9)
        self.assertFalse(controller.is_open())

        controller.update(pressure=15.5, temperature=122.0)
        self.assertTrue(controller.is_open())

    def test_emergency_overpressure_trip(self):
        controller = ValveController(target_pressure=15.0, target_temperature=121.0, max_safe_pressure=14.0, max_safe_temperature=250.0)

        # Temperature is low, but pressure exceeds emergency safe limit (14.0 PSI)
        controller.update(pressure=14.5, temperature=80.0)
        self.assertTrue(controller.is_open(), "Valve should open immediately during emergency overpressure")
        self.assertTrue(controller.is_emergency_tripped(), "Controller should register emergency trip state")

    def test_emergency_overtemp_trip(self):
        controller = ValveController(target_pressure=15.0, target_temperature=121.0, max_safe_pressure=14.0, max_safe_temperature=250.0)

        # Pressure is zero, but temperature exceeds emergency safe limit (250.0 °C)
        controller.update(pressure=0.0, temperature=255.0)
        self.assertTrue(controller.is_open(), "Valve should open immediately during emergency overtemp")
        self.assertTrue(controller.is_emergency_tripped(), "Controller should register emergency trip state")

    def test_latching_behavior(self):
        controller = ValveController(target_pressure=15.0, target_temperature=121.0, max_safe_pressure=18.0, max_safe_temperature=250.0)
        controller.update(pressure=15.0, temperature=121.0)
        self.assertTrue(controller.is_open())

        # Pressure drops after valve opens
        controller.update(pressure=0.0, temperature=100.0)
        self.assertTrue(controller.is_open())

    def test_reset(self):
        controller = ValveController()
        controller.update(pressure=15.0, temperature=121.0)
        self.assertTrue(controller.is_open())
        controller.reset()
        self.assertFalse(controller.is_open())
        self.assertFalse(controller.is_emergency_tripped())

if __name__ == '__main__':
    unittest.main()
