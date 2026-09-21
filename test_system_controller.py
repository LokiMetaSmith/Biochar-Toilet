import unittest
import time
from system_controller import SystemController, State
from heater_controller import HeaterController
from valve_controller import ValveController

class TestSystemController(unittest.TestCase):
    def setUp(self):
        self.heater = HeaterController()
        self.valve = ValveController()
        self.sys = SystemController(self.heater, self.valve)

    def test_initial_state(self):
        self.assertEqual(self.sys.state, State.OFF)
        self.assertEqual(self.sys.get_led_state(), "SOLID_GREEN")

    def test_negative_pressure_failure(self):
        self.sys.update(pressure=0.0, temperature=20.0, current_time_ms=0)
        self.assertEqual(self.sys.state, State.OFF)

        # One reading below -0.2
        self.sys.update(pressure=-0.3, temperature=20.0, current_time_ms=100)
        self.assertEqual(self.sys.state, State.OFF)

        # Second reading
        self.sys.update(pressure=-0.3, temperature=20.0, current_time_ms=200)
        self.assertEqual(self.sys.state, State.OFF)

        # Third reading should trip it
        self.sys.update(pressure=-0.3, temperature=20.0, current_time_ms=300)
        self.assertEqual(self.sys.state, State.ERROR)
        self.assertTrue(self.sys.valve.is_open())
        self.assertFalse(self.sys.heater.is_on())
        self.assertEqual(self.sys.get_led_state(), "FLASHING_RED")

    def test_runaway_absolute_temp(self):
        self.sys.transition_to(State.OFF, current_temp=20.0, current_time_ms=0)
        self.sys.update(pressure=0.0, temperature=30.0, current_time_ms=100)

        # Rise of 10 should trip because it is > 5C (and not in grace period)
        self.assertEqual(self.sys.state, State.ERROR)

    def test_runaway_absolute_temp_50C(self):
        self.sys.transition_to(State.COOLING, current_temp=100.0, current_time_ms=0)

        # Drop to 90C
        self.sys.update(pressure=0.0, temperature=90.0, current_time_ms=1000)

        # Immediate rise of 49C in grace period
        self.sys.update(pressure=0.0, temperature=139.0, current_time_ms=2000)
        self.assertEqual(self.sys.state, State.COOLING)

        # Rise to 140C (50C from minimum) in grace period trips absolute
        self.sys.update(pressure=0.0, temperature=140.0, current_time_ms=3000)
        self.assertEqual(self.sys.state, State.ERROR)

    def test_runaway_temp_off_state(self):
        self.sys.transition_to(State.OFF, current_temp=20.0, current_time_ms=0)

        self.sys.update(pressure=0.0, temperature=24.9, current_time_ms=100)
        self.assertEqual(self.sys.state, State.OFF)

        # Should trip error at >= 5C cumulative rise
        self.sys.update(pressure=0.0, temperature=25.0, current_time_ms=200)
        self.assertEqual(self.sys.state, State.ERROR)

    def test_cooling_runaway_grace_period(self):
        self.sys.transition_to(State.COOLING, current_temp=100.0, current_time_ms=0)

        # In grace period, 10C rise is ignored
        self.sys.update(pressure=0.0, temperature=110.0, current_time_ms=30000) # 30s
        self.assertEqual(self.sys.state, State.COOLING)

        # After grace period, if it rises 5C from its minimum, it fails
        self.sys.update(pressure=0.0, temperature=100.0, current_time_ms=65000) # drops back to 100

        self.sys.update(pressure=0.0, temperature=105.0, current_time_ms=70000) # rises 5C
        self.assertEqual(self.sys.state, State.ERROR)

    def test_stagnation(self):
        self.sys.transition_to(State.HEATING, current_temp=20.0, current_time_ms=0)

        self.sys.update(pressure=0.0, temperature=21.0, current_time_ms=60000)
        self.sys.update(pressure=0.0, temperature=22.0, current_time_ms=120000)
        self.assertEqual(self.sys.state, State.HEATING)

        # 180 seconds have passed, total rise is 2C (< 3C)
        self.sys.update(pressure=0.0, temperature=22.5, current_time_ms=180000)
        self.assertEqual(self.sys.state, State.ERROR)

    def test_no_stagnation_when_heating(self):
        self.sys.transition_to(State.HEATING, current_temp=20.0, current_time_ms=0)

        self.sys.update(pressure=0.0, temperature=25.0, current_time_ms=60000)
        self.sys.update(pressure=0.0, temperature=30.0, current_time_ms=120000)
        self.assertEqual(self.sys.state, State.HEATING)

        # 180 seconds have passed, total rise is 15C (>= 3C)
        self.sys.update(pressure=0.0, temperature=35.0, current_time_ms=180000)
        self.assertEqual(self.sys.state, State.HEATING)

if __name__ == '__main__':
    unittest.main()
