"""
test_heater_controller.py — Comprehensive Unit Test Suite for HeaterController.

Tests operational performance, hysteresis duty cycle scaling, time-window PWM output,
dry boiler protection interlocks, and over-temperature safety cutoffs.
"""

import unittest
from heater_controller import HeaterController

class TestHeaterController(unittest.TestCase):
    def test_initial_state(self):
        controller = HeaterController()
        self.assertFalse(controller.is_on())
        self.assertFalse(controller.is_overtemp_tripped())
        self.assertEqual(controller.duty_cycle, 0.0)

    def test_duty_cycle_computation(self):
        controller = HeaterController(target_setpoint=200.0, hysteresis=2.0, kp=0.03)

        # Well below setpoint (error = 100°C -> duty = 0.03 * 100 = 3.0 -> clamped to 1.0 / 100%)
        self.assertEqual(controller.compute_duty_cycle(100.0), 1.0)

        # Approaching setpoint (error = 10°C -> duty = 0.03 * 10 = 0.3 / 30%)
        self.assertAlmostEqual(controller.compute_duty_cycle(190.0), 0.3)

        # At setpoint (error = 0°C -> duty = 0.0)
        self.assertEqual(controller.compute_duty_cycle(200.0), 0.0)

        # In hysteresis band (201°C < 202°C -> error = -1°C -> duty = 0.0)
        self.assertEqual(controller.compute_duty_cycle(201.0), 0.0)

        # Above setpoint + hysteresis (203°C >= 202°C -> duty = 0.0)
        self.assertEqual(controller.compute_duty_cycle(203.0), 0.0)

    def test_pwm_window(self):
        controller = HeaterController(target_setpoint=200.0, hysteresis=2.0, kp=0.03, window_ms=2000)

        # At 190°C (duty = 30% -> active for 600ms of 2000ms window)
        # Time t=100ms (within active 600ms) -> ON
        self.assertTrue(controller.update(current_temp=190.0, now_ms=100))

        # Time t=700ms (past active 600ms) -> OFF
        self.assertFalse(controller.update(current_temp=190.0, now_ms=700))

        # Time t=2100ms (new window start, within active period) -> ON
        self.assertTrue(controller.update(current_temp=190.0, now_ms=2100))

    def test_dry_latched_interlock(self):
        controller = HeaterController(target_setpoint=200.0)

        # Below setpoint but dry state latched -> heater must stay OFF
        self.assertFalse(controller.update(current_temp=100.0, now_ms=100, dry_latched=True))
        self.assertEqual(controller.duty_cycle, 0.0)
        self.assertFalse(controller.is_on())

    def test_overtemp_safety_trip(self):
        controller = HeaterController(target_setpoint=200.0, max_safe_temp=250.0)

        # Temp exceeds 250°C safety cutoff
        self.assertFalse(controller.update(current_temp=255.0, now_ms=100))
        self.assertTrue(controller.is_overtemp_tripped())

        # Sub-setpoint temp after trip -> heater MUST remain OFF until reset
        self.assertFalse(controller.update(current_temp=150.0, now_ms=200))
        self.assertTrue(controller.is_overtemp_tripped())

    def test_reset(self):
        controller = HeaterController()
        controller.update(current_temp=260.0, now_ms=100)
        self.assertTrue(controller.is_overtemp_tripped())

        controller.reset()
        self.assertFalse(controller.is_overtemp_tripped())
        self.assertFalse(controller.is_on())

if __name__ == '__main__':
    unittest.main()
