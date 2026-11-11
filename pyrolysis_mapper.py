#!/usr/bin/env python3
"""
pyrolysis_mapper.py — Pyrolysis Cycle Estimator and Data Logger / Telemetry Replayer.

Parses ESP32-H2 serial output or recorded log files and calculates estimated
cycle dwell times based on sample mass.
"""

import sys
import time
import math
import csv
import re
import argparse
from datetime import datetime

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


def find_serial_ports():
    if not SERIAL_AVAILABLE:
        return []
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]


def select_serial_port():
    ports = find_serial_ports()
    if not ports:
        print("No serial ports found. Please connect the device and try again.")
        sys.exit(1)

    print("\nAvailable serial ports:")
    for i, port in enumerate(ports):
        print(f"[{i}] {port}")

    while True:
        try:
            choice = input("\nSelect a port by number: ")
            index = int(choice)
            if 0 <= index < len(ports):
                return ports[index]
            else:
                print("Invalid choice, please select a valid number.")
        except ValueError:
            print("Please enter a valid number.")


def estimate_cycle_time(mass_g):
    """
    Estimates pyrolysis dwell time in minutes using an exponential model:
    Time = k * (mass_g)^1.5, calibrated to 88g water = 120 minutes.
    """
    if mass_g <= 0:
        return 0.0

    k = 120.0 / math.pow(88.0, 1.5)
    return k * math.pow(mass_g, 1.5)


def parse_line_for_pressure(line):
    """
    Extracts pressure in PSI from lines containing 'P=<val>psi' or 'P=<val> PSI'.
    """
    match = re.search(r'P=([-\d\.]+)[\s]*psi', line, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def parse_line_for_temp(line):
    """
    Extracts temperature in °C from lines containing 'T_ema=<val>' or 'T=<val>°C'.
    """
    match = re.search(r'T(?:_ema)?=([-\d\.]+)', line)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def process_telemetry_stream(lines_iterable, mass_g, estimated_mins, output_csv=None, max_records=None):
    """
    Processes an iterable stream of serial lines, pairs pressure and temperature telemetry,
    and logs the calculated cycle progress to an optional CSV destination.

    Returns:
        list of dicts containing the parsed and recorded telemetry records.
    """
    records = []
    start_time = time.time()
    last_pressure = None

    csv_file = None
    writer = None
    if output_csv:
        csv_file = open(output_csv, mode='w', newline='')
        writer = csv.writer(csv_file)
        writer.writerow([
            "Timestamp",
            "Elapsed_Time_Mins",
            "Mass_g",
            "Estimated_Total_Time_Mins",
            "Pressure_PSI",
            "Temp_C",
            "Pyrolysis_State_Estimate_%"
        ])

    try:
        for line in lines_iterable:
            if not line:
                continue

            # Strip whitespace
            clean_line = line.strip()

            p = parse_line_for_pressure(clean_line)
            if p is not None:
                last_pressure = p

            t = parse_line_for_temp(clean_line)

            if t is not None and last_pressure is not None:
                current_time = time.time()
                elapsed_mins = (current_time - start_time) / 60.0

                progress_pct = (elapsed_mins / estimated_mins) * 100.0 if estimated_mins > 0 else 0.0
                if progress_pct > 100.0:
                    progress_pct = 100.0

                record = {
                    "timestamp": datetime.now().isoformat(),
                    "elapsed_mins": round(elapsed_mins, 2),
                    "mass_g": mass_g,
                    "estimated_total_mins": round(estimated_mins, 2),
                    "pressure_psi": round(last_pressure, 2),
                    "temp_c": round(t, 2),
                    "progress_pct": round(progress_pct, 1)
                }
                records.append(record)

                if writer:
                    writer.writerow([
                        record["timestamp"],
                        f"{record['elapsed_mins']:.2f}",
                        f"{record['mass_g']:.2f}",
                        f"{record['estimated_total_mins']:.2f}",
                        f"{record['pressure_psi']:.2f}",
                        f"{record['temp_c']:.2f}",
                        f"{record['progress_pct']:.1f}"
                    ])
                    csv_file.flush()

                last_pressure = None

                if max_records is not None and len(records) >= max_records:
                    break

    finally:
        if csv_file:
            csv_file.close()

    return records


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Pyrolysis Cycle Estimator and Data Logger")
    parser.add_argument("--mass", type=float, default=None, help="Input sample mass in grams (e.g. 88.0)")
    parser.add_argument("--port", type=str, default=None, help="Serial port device (e.g. /dev/ttyUSB0 or COM3)")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate (default: 115200)")
    parser.add_argument("--file", "--replay", dest="replay_file", type=str, default=None, help="Replay telemetry from an existing log file")
    parser.add_argument("--output-csv", type=str, default=None, help="Custom output CSV filename")
    parser.add_argument("--dry-run", action="store_true", help="Print parsed estimates without connecting or logging")
    return parser


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    print("=== Pyrolysis Cycle Estimator and Data Logger ===")

    # Determine mass
    if args.mass is not None:
        mass_g = args.mass
    else:
        try:
            mass_input = input("Enter the input sample mass of water in grams (e.g. 88): ")
            mass_g = float(mass_input)
        except ValueError:
            print("Invalid mass entered. Exiting.")
            sys.exit(1)

    estimated_mins = estimate_cycle_time(mass_g)
    print(f"\nEstimated Dwell Time for {mass_g}g: {estimated_mins:.2f} minutes ({estimated_mins/60.0:.2f} hours)\n")

    if args.dry_run:
        print("[Dry Run] Finished calculation. Exiting.")
        return

    csv_filename = args.output_csv
    if not csv_filename:
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"pyrolysis_log_{timestamp_str}.csv"

    print(f"Logging data to: {csv_filename}")

    # Replay mode from file
    if args.replay_file:
        print(f"Replaying telemetry from file: {args.replay_file}")
        with open(args.replay_file, "r", encoding="utf-8", errors="replace") as f:
            records = process_telemetry_stream(f, mass_g, estimated_mins, output_csv=csv_filename)
        print(f"Replay complete. Processed {len(records)} records. Data saved to {csv_filename}")
        return

    # Live serial mode
    if not SERIAL_AVAILABLE:
        print("Error: pyserial is required for live serial capture. Install with `pip install pyserial`.")
        sys.exit(1)

    port_name = args.port
    if not port_name:
        port_name = select_serial_port()

    print(f"\nConnecting to {port_name} at {args.baud} baud...")
    print("Press Ctrl+C to stop logging.\n")

    try:
        ser = serial.Serial(port_name, args.baud, timeout=1.0)
    except Exception as e:
        print(f"Failed to open serial port {port_name}: {e}")
        sys.exit(1)

    def serial_line_generator():
        while True:
            line = ser.readline().decode('utf-8', errors='replace')
            if not line:
                continue
            print(f"[Serial] {line.strip()}")
            yield line

    try:
        process_telemetry_stream(serial_line_generator(), mass_g, estimated_mins, output_csv=csv_filename)
    except KeyboardInterrupt:
        print("\nLogging stopped by user.")
    finally:
        ser.close()
        print(f"Data saved to {csv_filename}")


if __name__ == "__main__":
    main()
