
import csv
import json
import argparse
from collections import Counter
from datetime import datetime


class TimestampValidator:
    """Offline timestamp-quality validator for recorded sensor datasets."""

    def __init__(self, csv_path, timestamp_column="timestamp",
                 unit="seconds", expected_rate_hz=50.0):
        self.csv_path = csv_path
        self.timestamp_column = timestamp_column
        self.unit = unit
        self.expected_rate_hz = expected_rate_hz
        self.timestamps = []
        self.results = {}

    def load_data(self):
        with open(self.csv_path, "r", newline="") as file:
            reader = csv.DictReader(file)

            if not reader.fieldnames:
                raise ValueError("CSV has no header.")

            if self.timestamp_column not in reader.fieldnames:
                self.results["timestamp_field_availability"] = {
                    "status": "FAIL",
                    "detail": f"Column '{self.timestamp_column}' not found."
                }
                return

            self.results["timestamp_field_availability"] = {
                "status": "PASS",
                "detail": f"Column '{self.timestamp_column}' found."
            }

            for row in reader:
                value = row.get(self.timestamp_column, "").strip()

                if not value:
                    self.timestamps.append(None)
                    continue

                try:
                    self.timestamps.append(float(value))
                except ValueError:
                    self.timestamps.append(None)

    def check_missing(self):
        missing = sum(value is None for value in self.timestamps)

        self.results["missing_timestamps"] = {
            "status": "PASS" if missing == 0 else "FAIL",
            "count": missing
        }

    def check_duplicates(self):
        valid = [x for x in self.timestamps if x is not None]
        counts = Counter(valid)
        duplicates = sum(count - 1 for count in counts.values())

        self.results["duplicate_timestamps"] = {
            "status": "PASS" if duplicates == 0 else "FAIL",
            "count": duplicates
        }

    def check_monotonicity(self):
        valid = [x for x in self.timestamps if x is not None]
        regressions = sum(
            current < previous
            for previous, current in zip(valid, valid[1:])
        )

        self.results["timestamp_monotonicity"] = {
            "status": "PASS" if regressions == 0 else "FAIL",
            "regressions": regressions
        }

    def check_recording_gaps(self):
        valid = [x for x in self.timestamps if x is not None]

        if len(valid) < 2:
            self.results["recording_gaps"] = {
                "status": "NOT_TESTED",
                "detail": "Insufficient valid timestamps."
            }
            return

        intervals = [
            current - previous
            for previous, current in zip(valid, valid[1:])
        ]

        expected_period = 1.0 / self.expected_rate_hz
        threshold = expected_period * 1.5

        gaps = [
            interval for interval in intervals
            if interval > threshold
        ]

        self.results["recording_gaps"] = {
            "status": "PASS" if not gaps else "WARNING",
            "gap_count": len(gaps),
            "maximum_interval": max(intervals),
            "expected_interval": expected_period
        }

    def check_units_and_format(self):
        valid = [x for x in self.timestamps if x is not None]

        supported_units = {
            "seconds": 1.0,
            "milliseconds": 1e-3,
            "microseconds": 1e-6,
            "nanoseconds": 1e-9
        }

        if self.unit not in supported_units:
            status = "FAIL"
            detail = "Unsupported unit."
        elif not valid:
            status = "NOT_TESTED"
            detail = "No valid timestamps."
        else:
            status = "PASS"
            detail = f"Numeric timestamps; declared unit: {self.unit}."

        self.results["timestamp_units_and_format"] = {
            "status": status,
            "unit": self.unit,
            "detail": detail
        }

    def run(self):
        self.load_data()

        if self.results.get(
            "timestamp_field_availability", {}
        ).get("status") == "FAIL":
            return self.results

        self.check_missing()
        self.check_duplicates()
        self.check_monotonicity()
        self.check_recording_gaps()
        self.check_units_and_format()

        return self.results

    def save_report(self, output_path="timestamp_report.json"):
        with open(output_path, "w") as file:
            json.dump(self.results, file, indent=4)

        print(f"\nReport saved: {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--column", default="timestamp")
    parser.add_argument("--unit", default="seconds")
    parser.add_argument("--rate", type=float, default=50.0)
    args = parser.parse_args()

    validator = TimestampValidator(
        csv_path=args.csv,
        timestamp_column=args.column,
        unit=args.unit,
        expected_rate_hz=args.rate
    )

    results = validator.run()

    print("\n===== TIMESTAMP VALIDATION =====")

    for check, result in results.items():
        print(f"\n{check}:")
        print(json.dumps(result, indent=4))

    validator.save_report()


if __name__ == "__main__":
    main()
