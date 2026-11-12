"""Measure Strix RAW_IMU timing and save CSV/JSON summaries."""

# 1. IMPORTS
import csv
import json
import statistics
import time
from datetime import datetime
from pathlib import Path

from pymavlink import mavutil


# 2. CONFIGURATION
class Configuration:
    STRIX_PORT = (
        "/dev/serial/by-id/"
        "usb-ArduPilot_Zerodrag_Strix_R0.1_"
        "310032001551343131393036-if00"
    )
    BAUD_RATE = 115200
    TEST_DURATION_S = 60
    REQUESTED_RATE_HZ = 50
    HEARTBEAT_TIMEOUT_S = 10
    MESSAGE_TIMEOUT_S = 1
    GAP_WARNING_S = 0.100
    GAP_CRITICAL_S = 0.500


# 3. CORE LOGIC
class Logic:
    def __init__(self, config):
        self.config = config
        self.connection = None

    def connect_to_strix(self):
        print(f"Connecting to Strix: {self.config.STRIX_PORT}")
        self.connection = mavutil.mavlink_connection(
            self.config.STRIX_PORT, baud=self.config.BAUD_RATE
        )
        if self.connection.wait_heartbeat(
            timeout=self.config.HEARTBEAT_TIMEOUT_S
        ) is None:
            raise TimeoutError("No MAVLink heartbeat received.")
        print(
            f"Heartbeat received: system={self.connection.target_system}, "
            f"component={self.connection.target_component}"
        )

    def request_imu_stream(self):
        if self.connection is None:
            raise RuntimeError("Strix is not connected.")
        self.connection.mav.command_long_send(
            self.connection.target_system,
            self.connection.target_component,
            mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
            0,
            mavutil.mavlink.MAVLINK_MSG_ID_RAW_IMU,
            int(1_000_000 / self.config.REQUESTED_RATE_HZ),
            0, 0, 0, 0, 0,
        )
        print(f"Requested RAW_IMU rate: {self.config.REQUESTED_RATE_HZ} Hz")

    def capture_measurements(self):
        if self.connection is None:
            raise RuntimeError("Strix is not connected.")

        measurements = []
        print("Allowing stream to settle...")
        time.sleep(2)
        start_ns = time.monotonic_ns()
        deadline_ns = start_ns + self.config.TEST_DURATION_S * 1_000_000_000
        print(f"Capturing for {self.config.TEST_DURATION_S} seconds...")

        while time.monotonic_ns() < deadline_ns:
            message = self.connection.recv_match(
                type="RAW_IMU", blocking=True,
                timeout=self.config.MESSAGE_TIMEOUT_S,
            )
            host_ns = time.monotonic_ns()
            if message is None:
                continue

            measurements.append({
                "sample_index": len(measurements) + 1,
                "sensor_time_usec": int(message.time_usec),
                "host_receive_monotonic_ns": host_ns,
            })
            if len(measurements) % 250 == 0:
                print(f"Captured {len(measurements)} samples")

        elapsed_s = (time.monotonic_ns() - start_ns) / 1_000_000_000
        print(f"Captured {len(measurements)} samples in {elapsed_s:.3f} s")
        return measurements, elapsed_s

    def write_csv(self, measurements, output_dir):
        path = output_dir / "raw_measurements.csv"
        fields = [
            "sample_index", "sensor_time_usec", "host_receive_monotonic_ns"
        ]
        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(measurements)
        print(f"Raw data saved: {path}")

    def analyze_timestamps(self, measurements, elapsed_s):
        if len(measurements) < 2:
            return {
                "status": "INSUFFICIENT_DATA",
                "sample_count": len(measurements),
                "elapsed_s": round(elapsed_s, 6),
            }

        sensor = [row["sensor_time_usec"] / 1_000_000 for row in measurements]
        host = [
            row["host_receive_monotonic_ns"] / 1_000_000_000
            for row in measurements
        ]
        sensor_dt = [b - a for a, b in zip(sensor, sensor[1:])]
        host_dt = [b - a for a, b in zip(host, host[1:])]

        def interval_stats(intervals):
            positive = [value for value in intervals if value > 0]
            if not positive:
                return {
                    "positive_interval_count": 0,
                    "monotonic": False,
                    "intervals_over_100ms": sum(
                        value > self.config.GAP_WARNING_S for value in intervals
                    ),
                    "intervals_over_500ms": sum(
                        value > self.config.GAP_CRITICAL_S for value in intervals
                    ),
                }

            mean_s = statistics.mean(positive)
            expected_s = 1 / self.config.REQUESTED_RATE_HZ
            return {
                "positive_interval_count": len(positive),
                "mean_interval_ms": round(mean_s * 1000, 3),
                "median_interval_ms": round(statistics.median(positive) * 1000, 3),
                "min_positive_interval_ms": round(min(positive) * 1000, 3),
                "max_interval_ms": round(max(intervals) * 1000, 3),
                "interval_stddev_ms": round(statistics.pstdev(positive) * 1000, 3),
                "jitter_from_requested_period_ms": round(
                    statistics.mean(abs(value - expected_s) for value in positive)
                    * 1000, 3
                ),
                "intervals_over_100ms": sum(
                    value > self.config.GAP_WARNING_S for value in intervals
                ),
                "intervals_over_500ms": sum(
                    value > self.config.GAP_CRITICAL_S for value in intervals
                ),
                "monotonic": all(value > 0 for value in intervals),
            }

        sensor_stats = interval_stats(sensor_dt)
        host_stats = interval_stats(host_dt)
        status = (
            "CAPTURE_REVIEWED_NO_CRITICAL_GAPS"
            if sensor_stats["monotonic"] and host_stats["monotonic"]
            and sensor_stats["intervals_over_500ms"] == 0
            and host_stats["intervals_over_500ms"] == 0
            else "REVIEW_REQUIRED"
        )
        return {
            "status": status,
            "sample_count": len(measurements),
            "elapsed_s": round(elapsed_s, 6),
            "requested_rate_hz": self.config.REQUESTED_RATE_HZ,
            "observed_message_rate_hz": round((len(measurements) - 1) / elapsed_s, 3)
                if elapsed_s > 0 else 0,
            "sensor_timestamp": sensor_stats,
            "host_arrival_timestamp": host_stats,
            "sensor_nonpositive_intervals": sum(value <= 0 for value in sensor_dt),
            "host_nonpositive_intervals": sum(value <= 0 for value in host_dt),
            "note": (
                "Host timestamps are software-observed arrival times; this report "
                "does not establish absolute clock synchronization or exact "
                "IMU acquisition time."
            ),
        }

    def write_report(self, report, output_dir):
        json_path = output_dir / "timing_report.json"
        json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        summary_path = output_dir / "summary.txt"
        summary_path.write_text(
            "STRIX TIMING CHARACTERIZATION\n"
            f"Status: {report['status']}\n"
            f"Samples: {report['sample_count']}\n"
            f"Elapsed: {report.get('elapsed_s', 'N/A')} seconds\n"
            f"Observed rate: {report.get('observed_message_rate_hz', 'N/A')} Hz\n"
            "Details: timing_report.json\n",
            encoding="utf-8",
        )
        print(f"Reports saved: {json_path}, {summary_path}")

    def close_connection(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None
            print("Strix connection closed.")

    def run(self):
        output_dir = Path.home() / "strix_timing_data" / datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            self.connect_to_strix()
            self.request_imu_stream()
            measurements, elapsed_s = self.capture_measurements()
            self.write_csv(measurements, output_dir)
            report = self.analyze_timestamps(measurements, elapsed_s)
            self.write_report(report, output_dir)
            print(f"Timing test finished. Output: {output_dir}")
        finally:
            self.close_connection()


def main():
    logic = Logic(Configuration())
    try:
        logic.run()
    except Exception as exc:
        print(f"Timing test failed: {type(exc).__name__}: {exc}")
        raise
    finally:
        logic.close_connection()


if __name__ == "__main__":
    main()