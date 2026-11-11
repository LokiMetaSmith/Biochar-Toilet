"""
test_pyrolysis_mapper.py — Unit Test Suite for pyrolysis_mapper.py.

Tests:
  - Exponential cycle time estimation model across various masses.
  - Telemetry line regex extraction for pressure and temperature.
  - Streaming line processor pairing pressure and temperature.
  - CLI argument parsing for headless, replay, and dry-run workflows.
"""

import unittest
import tempfile
import os
from pyrolysis_mapper import (
    estimate_cycle_time,
    parse_line_for_pressure,
    parse_line_for_temp,
    process_telemetry_stream,
    build_arg_parser
)


class TestPyrolysisMapper(unittest.TestCase):
    def test_estimate_cycle_time(self):
        # Baseline: 88g water = 120 minutes
        self.assertAlmostEqual(estimate_cycle_time(88.0), 120.0, places=2)

        # 0g or negative mass returns 0.0
        self.assertEqual(estimate_cycle_time(0.0), 0.0)
        self.assertEqual(estimate_cycle_time(-10.0), 0.0)

        # Higher mass takes disproportionately longer (superlinear scaling)
        time_44g = estimate_cycle_time(44.0)
        time_88g = estimate_cycle_time(88.0)
        time_176g = estimate_cycle_time(176.0)

        self.assertLess(time_44g, time_88g)
        self.assertGreater(time_176g, time_88g * 2)  # because n = 1.5

    def test_parse_line_for_pressure(self):
        line1 = "P=12.34psi | Valve=CLOSED | Pump=OFF"
        self.assertEqual(parse_line_for_pressure(line1), 12.34)

        line2 = "[Serial] P=0.50 PSI | Status=OK"
        self.assertEqual(parse_line_for_pressure(line2), 0.50)

        line3 = "P=-0.25psi"
        self.assertEqual(parse_line_for_pressure(line3), -0.25)

        line_no_p = "Valve=CLOSED | Pump=OFF"
        self.assertIsNone(parse_line_for_pressure(line_no_p))

    def test_parse_line_for_temp(self):
        line1 = "T_ema=123.4°C"
        self.assertEqual(parse_line_for_temp(line1), 123.4)

        line2 = "Current T=205.8 | Heater=ON"
        self.assertEqual(parse_line_for_temp(line2), 205.8)

        line_no_t = "P=10.0psi | Valve=OPEN"
        self.assertIsNone(parse_line_for_temp(line_no_t))

    def test_process_telemetry_stream(self):
        lines = [
            "P=8.50psi | Valve=CLOSED",
            "T_ema=115.0°C",
            "P=8.40psi | Valve=OPEN",
            "T_ema=120.5°C"
        ]

        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.csv') as tmp_csv:
            csv_path = tmp_csv.name

        try:
            records = process_telemetry_stream(
                lines_iterable=lines,
                mass_g=88.0,
                estimated_mins=120.0,
                output_csv=csv_path
            )

            self.assertEqual(len(records), 2)
            self.assertEqual(records[0]["pressure_psi"], 8.50)
            self.assertEqual(records[0]["temp_c"], 115.0)
            self.assertEqual(records[1]["pressure_psi"], 8.40)
            self.assertEqual(records[1]["temp_c"], 120.5)

            # Check that file was written with header + 2 data rows
            with open(csv_path, 'r') as f:
                content = f.readlines()
            self.assertEqual(len(content), 3)
            self.assertIn("Timestamp,Elapsed_Time_Mins,Mass_g", content[0])
        finally:
            if os.path.exists(csv_path):
                os.remove(csv_path)

    def test_cli_argument_parsing(self):
        parser = build_arg_parser()

        args = parser.parse_args(["--mass", "100", "--port", "/dev/ttyUSB0", "--dry-run"])
        self.assertEqual(args.mass, 100.0)
        self.assertEqual(args.port, "/dev/ttyUSB0")
        self.assertTrue(args.dry_run)

        replay_args = parser.parse_args(["--replay", "sample.log", "--output-csv", "out.csv"])
        self.assertEqual(replay_args.replay_file, "sample.log")
        self.assertEqual(replay_args.output_csv, "out.csv")


if __name__ == '__main__':
    unittest.main()
