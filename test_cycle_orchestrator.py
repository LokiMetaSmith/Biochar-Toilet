"""
test_cycle_orchestrator.py — Comprehensive Unit Test Suite for CycleOrchestrator.

Tests full lifecycle state machine:
  - Transition from IDLE to HEATING on cycle start.
  - Transition from HEATING to CHARRING upon dryness detection.
  - Transition from CHARRING to COOLING after dwell duration.
  - Safe transition from COOLING back to IDLE when safe temp reached.
  - Safety interlocks:
    * Negative pressure fault trip.
    * Overpressure trip.
    * Overtemperature trip.
    * Absolute thermal runaway (+50°C in IDLE/COOLING).
    * Low-temperature runaway (+5°C after grace period in COOLING/IDLE).
    * Thermal stagnation (<3°C rise over 1 hour in HEATING).
"""

import unittest
from cycle_orchestrator import CycleOrchestrator, CycleState
from heater_controller import HeaterController
from valve_controller import ValveController
from dryness_monitor import DrynessMonitor


class TestCycleOrchestrator(unittest.TestCase):
    def setUp(self):
        self.heater = HeaterController(target_setpoint=130.0, max_safe_temp=250.0)
        self.valve = ValveController(target_pressure=8.0, min_seal_pressure=4.0, max_safe_pressure=18.0)
        self.dryness = DrynessMonitor(min_temp_rate=0.5, max_pressure_rate=0.1)
        self.orchestrator = CycleOrchestrator(
            heater_controller=self.heater,
            valve_controller=self.valve,
            dryness_monitor=self.dryness,
            drying_temp_setpoint=130.0,
            charring_temp_setpoint=220.0,
            charring_duration_ms=60000,   # 1 minute dwell for test
            cooling_safe_temp=50.0,
            stagnation_window_ms=3600000,
            stagnation_min_rise_c=3.0,
            runaway_grace_ms=3600000
        )

    def test_initial_state(self):
        self.assertEqual(self.orchestrator.state, CycleState.IDLE)
        self.assertFalse(self.orchestrator.heater.is_on())
        self.assertFalse(self.orchestrator.valve.is_open())

    def test_normal_cycle_progression(self):
        # 1. Start cycle -> HEATING
        self.assertTrue(self.orchestrator.start_cycle(current_time_ms=0))
        self.assertEqual(self.orchestrator.state, CycleState.HEATING)
        self.assertEqual(self.orchestrator.heater.target_setpoint, 130.0)

        # 2. Simulate wet heating phase: temp rises, pressure rises -> stays HEATING
        for t in range(5):
            self.orchestrator.update(pressure=5.0 + t * 0.5, temperature=90.0 + t * 2.0, current_time_ms=t * 1000)
            self.assertEqual(self.orchestrator.state, CycleState.HEATING)

        # 3. Trigger dryness via ValveController dry_latched
        self.orchestrator.valve.dry_latched = True
        self.orchestrator.update(pressure=4.0, temperature=120.0, current_time_ms=10000)
        self.assertEqual(self.orchestrator.state, CycleState.CHARRING)
        self.assertEqual(self.orchestrator.heater.target_setpoint, 220.0)

        # 4. Stay in CHARRING until duration expires
        self.orchestrator.update(pressure=4.0, temperature=210.0, current_time_ms=50000)
        self.assertEqual(self.orchestrator.state, CycleState.CHARRING)

        # 5. Dwell expires -> transitions to COOLING
        self.orchestrator.update(pressure=4.0, temperature=220.0, current_time_ms=70001)
        self.assertEqual(self.orchestrator.state, CycleState.COOLING)
        self.assertFalse(self.orchestrator.heater.is_on())

        # 6. Cools down to safe temperature -> transitions to IDLE
        self.orchestrator.update(pressure=1.0, temperature=48.0, current_time_ms=100000)
        self.assertEqual(self.orchestrator.state, CycleState.IDLE)

    def test_negative_pressure_safety_trip(self):
        self.orchestrator.start_cycle(current_time_ms=0)

        # 2 negative readings should not trip yet
        self.orchestrator.update(pressure=-0.3, temperature=100.0, current_time_ms=1000)
        self.assertEqual(self.orchestrator.state, CycleState.HEATING)
        self.orchestrator.update(pressure=-0.3, temperature=100.0, current_time_ms=2000)
        self.assertEqual(self.orchestrator.state, CycleState.HEATING)

        # 3rd consecutive negative pressure reading -> triggers ERROR
        self.orchestrator.update(pressure=-0.3, temperature=100.0, current_time_ms=3000)
        self.assertEqual(self.orchestrator.state, CycleState.ERROR)
        self.assertTrue(self.orchestrator.valve.is_open())
        self.assertFalse(self.orchestrator.heater.is_on())

    def test_overpressure_safety_trip(self):
        self.orchestrator.start_cycle(current_time_ms=0)
        self.orchestrator.update(pressure=18.5, temperature=100.0, current_time_ms=1000)
        self.assertEqual(self.orchestrator.state, CycleState.ERROR)
        self.assertTrue(self.orchestrator.valve.is_open())
        self.assertFalse(self.orchestrator.heater.is_on())

    def test_overtemperature_safety_trip(self):
        self.orchestrator.start_cycle(current_time_ms=0)
        self.orchestrator.update(pressure=5.0, temperature=255.0, current_time_ms=1000)
        self.assertEqual(self.orchestrator.state, CycleState.ERROR)
        self.assertTrue(self.orchestrator.valve.is_open())
        self.assertFalse(self.orchestrator.heater.is_on())

    def test_absolute_thermal_runaway_in_idle(self):
        # Baseline established at 25C
        self.orchestrator.update(pressure=0.0, temperature=25.0, current_time_ms=0)
        self.assertEqual(self.orchestrator.state, CycleState.IDLE)

        # Sudden jump of >= 50C in IDLE without active cycle
        self.orchestrator.update(pressure=0.0, temperature=76.0, current_time_ms=1000)
        self.assertEqual(self.orchestrator.state, CycleState.ERROR)
        self.assertIn("Absolute thermal runaway", self.orchestrator.error_reason)

    def test_stuck_heater_thermal_runaway_after_grace_period(self):
        self.orchestrator.start_cycle(current_time_ms=0)
        # Advance to charring
        self.orchestrator.valve.dry_latched = True
        self.orchestrator.update(pressure=4.0, temperature=130.0, current_time_ms=1000)
        # Advance to cooling
        self.orchestrator.update(pressure=4.0, temperature=220.0, current_time_ms=61001)
        self.assertEqual(self.orchestrator.state, CycleState.COOLING)

        # Within 1-hour grace period, small rises don't trip
        self.orchestrator.update(pressure=1.0, temperature=100.0, current_time_ms=70000)
        self.orchestrator.update(pressure=1.0, temperature=106.0, current_time_ms=75000)
        self.assertEqual(self.orchestrator.state, CycleState.COOLING)

        # Set baseline after grace period has expired (e.g., at t = 3,700,000ms from cooling start 61001ms)
        post_grace_time = 61001 + 3600000 + 1000
        self.orchestrator.update(pressure=1.0, temperature=80.0, current_time_ms=post_grace_time)
        self.assertEqual(self.orchestrator.state, CycleState.COOLING)

        # Temperature rises by +5C after grace period -> trips ERROR
        self.orchestrator.update(pressure=1.0, temperature=85.5, current_time_ms=post_grace_time + 1000)
        self.assertEqual(self.orchestrator.state, CycleState.ERROR)
        self.assertIn("Stuck heater thermal runaway", self.orchestrator.error_reason)

    def test_stagnation_in_heating(self):
        self.orchestrator.start_cycle(current_time_ms=0)
        # Record initial reading at t=0
        self.orchestrator.update(pressure=2.0, temperature=50.0, current_time_ms=0)

        # Advance to nearly 1 hour with only 2.0C rise (< 3.0C)
        self.orchestrator.update(pressure=2.0, temperature=52.0, current_time_ms=3596000)
        self.assertEqual(self.orchestrator.state, CycleState.ERROR)
        self.assertIn("Heater stagnation", self.orchestrator.error_reason)

    def test_reset_error(self):
        self.orchestrator.trigger_error("Manual Test Error")
        self.assertEqual(self.orchestrator.state, CycleState.ERROR)
        self.assertTrue(self.orchestrator.valve.is_open())

        self.orchestrator.reset_error()
        self.assertEqual(self.orchestrator.state, CycleState.IDLE)
        self.assertIsNone(self.orchestrator.error_reason)
        self.assertFalse(self.orchestrator.valve.is_open())


if __name__ == '__main__':
    unittest.main()
