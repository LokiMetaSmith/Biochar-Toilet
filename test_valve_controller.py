import unittest
from valve_controller import ValveController

class TestValveController(unittest.TestCase):
    def test_initial_state(self):
        controller = ValveController()
        self.assertFalse(controller.is_open())
        self.assertFalse(controller.is_emergency_tripped())

    def test_minimum_seal_pressure_floor(self):
        controller = ValveController(target_pressure=8.0, target_temperature=121.0, min_seal_pressure=4.0, max_safe_pressure=18.0, max_safe_temperature=250.0)

        # Trigger release cycle first
        controller.update(pressure=8.0, temperature=121.0, current_time_ms=0)

        # Pressure drops to 4.0 PSI floor, valve should close and release should end
        controller.update(pressure=4.0, temperature=121.0, current_time_ms=500)
        self.assertFalse(controller.is_open())
        self.assertFalse(controller.release_active)

    def test_single_shot_duration_and_cooldown(self):
        # Window is 2000ms, cooldown is 2000ms
        controller = ValveController(target_pressure=8.0, target_temperature=121.0, min_seal_pressure=4.0, max_safe_pressure=18.0, max_safe_temperature=250.0, window_ms=2000, cooldown_ms=2000)

        # 1. Trigger release cycle at pressure = 8.0 (High pressure).
        # t = (8.0 - 4.0) / 4.0 = 1.0
        # duty = log1p(1.0 * 1.71828) = 1.0 -> duration = 2000ms
        controller.update(pressure=8.0, temperature=121.0, current_time_ms=0)
        self.assertTrue(controller.is_open())
        self.assertTrue(controller.release_active)

        # 2. Still open at 1000ms
        controller.update(pressure=8.0, temperature=121.0, current_time_ms=1000)
        self.assertTrue(controller.is_open())

        # 3. Burst finishes at 2000ms, valve should close and enter cooldown
        controller.update(pressure=8.0, temperature=121.0, current_time_ms=2000)
        self.assertFalse(controller.is_open())
        self.assertEqual(controller.cooldown_start_time, 2000)

        # 4. Still in cooldown at 3000ms, even with high pressure, valve should be closed
        controller.update(pressure=8.0, temperature=121.0, current_time_ms=3000)
        self.assertFalse(controller.is_open())

        # 5. Cooldown finishes at 4000ms, valve should start new burst
        # Let's test at pressure = 4.1 (Low pressure, just above floor).
        # t = (4.1 - 4.0) / 4.0 ~= 0.025
        # duty = log1p(0.025 * 1.71828) ~= 0.042 -> duration ~= 84ms
        controller.update(pressure=4.1, temperature=121.0, current_time_ms=4000)
        self.assertTrue(controller.is_open())

        # 6. Burst finishes quickly, should be closed at 4100ms
        controller.update(pressure=4.1, temperature=121.0, current_time_ms=4100)
        self.assertFalse(controller.is_open())
        self.assertEqual(controller.cooldown_start_time, 4100)

    def test_emergency_overpressure_trip(self):
        controller = ValveController(target_pressure=8.0, min_seal_pressure=4.0, max_safe_pressure=18.0, max_safe_temperature=250.0)

        # Pressure exceeds emergency safe limit (18.0 PSI)
        controller.update(pressure=18.5, temperature=80.0, current_time_ms=0)
        self.assertTrue(controller.is_open(), "Valve should open immediately during emergency overpressure")
        self.assertTrue(controller.is_emergency_tripped(), "Controller should register emergency trip state")

    def test_emergency_overtemp_trip(self):
        controller = ValveController(target_pressure=8.0, min_seal_pressure=4.0, max_safe_pressure=18.0, max_safe_temperature=250.0)

        # Temperature exceeds emergency safe limit (250.0 °C)
        controller.update(pressure=10.0, temperature=255.0, current_time_ms=0)
        self.assertTrue(controller.is_open(), "Valve should open immediately during emergency overtemp")
        self.assertTrue(controller.is_emergency_tripped(), "Controller should register emergency trip state")

    def test_emergency_latching_behavior(self):
        controller = ValveController(target_pressure=8.0, target_temperature=121.0, min_seal_pressure=4.0, max_safe_pressure=18.0, max_safe_temperature=250.0)

        # Trip emergency
        controller.update(pressure=19.0, temperature=121.0, current_time_ms=0)
        self.assertTrue(controller.is_open())

        # Pressure drops after emergency trip, valve should stay latched open
        controller.update(pressure=3.0, temperature=100.0, current_time_ms=100)
        self.assertTrue(controller.is_open())

    def test_normal_release_behavior(self):
        controller = ValveController(target_pressure=8.0, target_temperature=121.0, min_seal_pressure=4.0, max_safe_pressure=18.0, max_safe_temperature=250.0)

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
        controller = ValveController()
        controller.update(pressure=19.0, temperature=255.0, current_time_ms=0)
        self.assertTrue(controller.is_open())
        controller.reset(current_time_ms=100)
        self.assertFalse(controller.is_open())
        self.assertFalse(controller.is_emergency_tripped())

    def test_threshold_crossing(self):
        # A test to cover a previous lazy test issue: properly check threshold crossing
        controller = ValveController(target_pressure=8.0, target_temperature=121.0)

        # Start below threshold
        controller.update(pressure=7.9, temperature=120.9, current_time_ms=0)
        self.assertFalse(controller.release_active)

        # Cross temperature threshold, but not pressure
        controller.update(pressure=7.9, temperature=121.1, current_time_ms=100)
        self.assertFalse(controller.release_active)

        # Cross pressure threshold, but not temperature
        controller.update(pressure=8.1, temperature=120.9, current_time_ms=200)
        self.assertFalse(controller.release_active)

        # Cross both thresholds
        controller.update(pressure=8.1, temperature=121.1, current_time_ms=300)
        self.assertTrue(controller.release_active)

if __name__ == '__main__':
    unittest.main()
