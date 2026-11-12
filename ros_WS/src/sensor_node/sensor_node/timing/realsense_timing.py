"""
Module: RealSense D455 Timing Characterization
Purpose:
    Capture RGB and depth timing before sensor synchronization.

Outputs:
    raw_measurements.csv
    timing_report.json
    summary.txt
"""

# 1. IMPORTS
import csv
import json
import statistics
import time
from datetime import datetime
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


# 2. CONFIGURATION
class Configuration:
    RGB_TOPIC = "/camera/camera/color/image_raw"
    DEPTH_TOPIC = "/camera/camera/depth/image_rect_raw"

    TEST_DURATION_S = 60
    WARMUP_DURATION_S = 2
    REQUESTED_RATE_HZ = 30

    GAP_WARNING_S = 0.100
    GAP_CRITICAL_S = 0.500
    OUTPUT_ROOT = Path.home() / "strix_timing_data" / "realsense"


# 3. CORE LOGIC
class Logic(Node):

    def __init__(self, config: Configuration):
        super().__init__("realsense_timing_capture")
        self.config = config
        self.measurements = []
        self.sample_counts = {"rgb": 0, "depth": 0}
        self.capture_enabled = False

        self.create_subscription(
            Image, self.config.RGB_TOPIC, self.rgb_callback,
            qos_profile_sensor_data
        )
        self.create_subscription(
            Image, self.config.DEPTH_TOPIC, self.depth_callback,
            qos_profile_sensor_data
        )

    # Record RGB and depth messages
    def rgb_callback(self, message: Image):
        self.record_message("rgb", message)

    def depth_callback(self, message: Image):
        self.record_message("depth", message)

    def record_message(self, stream_name: str, message: Image):
        if not self.capture_enabled:
            return

        self.sample_counts[stream_name] += 1
        self.measurements.append({
            "stream": stream_name,
            "sample_index": self.sample_counts[stream_name],
            "sensor_timestamp_ns": (
                message.header.stamp.sec * 1_000_000_000
                + message.header.stamp.nanosec
            ),
            "host_receive_monotonic_ns": time.monotonic_ns(),
            "header_frame_id": message.header.frame_id,
        })

    # Capture raw measurements
    def capture_measurements(self):
        print("RGB topic:", self.config.RGB_TOPIC)
        print("Depth topic:", self.config.DEPTH_TOPIC)
        print(f"Warming up for {self.config.WARMUP_DURATION_S} seconds...")

        warmup_start = time.monotonic()
        while (
            rclpy.ok()
            and time.monotonic() - warmup_start < self.config.WARMUP_DURATION_S
        ):
            rclpy.spin_once(self, timeout_sec=0.1)

        self.measurements.clear()
        self.sample_counts = {"rgb": 0, "depth": 0}
        self.capture_enabled = True

        print(f"Capturing for {self.config.TEST_DURATION_S} seconds...")
        start_ns = time.monotonic_ns()
        deadline_ns = start_ns + self.config.TEST_DURATION_S * 1_000_000_000
        next_report_s = 10

        while rclpy.ok() and time.monotonic_ns() < deadline_ns:
            rclpy.spin_once(self, timeout_sec=0.1)
            elapsed_s = (time.monotonic_ns() - start_ns) / 1_000_000_000
            if elapsed_s >= next_report_s:
                print(
                    f"Elapsed {elapsed_s:.0f}s | RGB: {self.sample_counts['rgb']} | "
                    f"Depth: {self.sample_counts['depth']}"
                )
                next_report_s += 10

        elapsed_s = (time.monotonic_ns() - start_ns) / 1_000_000_000
        self.capture_enabled = False
        print(f"Capture complete: RGB={self.sample_counts['rgb']}, "
              f"Depth={self.sample_counts['depth']}, elapsed={elapsed_s:.3f}s")
        return list(self.measurements), elapsed_s

    # Analyze timestamp intervals
    def analyze_one_stream(self, rows, elapsed_s):
        if len(rows) < 2:
            return {"status": "INSUFFICIENT_DATA", "sample_count": len(rows)}

        def interval_stats(key):
            times = [row[key] for row in rows]
            intervals = [
                (times[i] - times[i - 1]) / 1e9
                for i in range(1, len(times))
            ]
            positive = [value for value in intervals if value > 0]
            if not positive:
                return {"monotonic": False, "nonpositive_intervals": len(intervals)}

            expected_s = 1 / self.config.REQUESTED_RATE_HZ
            return {
                "positive_interval_count": len(positive),
                "mean_interval_ms": round(statistics.mean(positive) * 1000, 3),
                "median_interval_ms": round(statistics.median(positive) * 1000, 3),
                "min_positive_interval_ms": round(min(positive) * 1000, 3),
                "max_interval_ms": round(max(intervals) * 1000, 3),
                "interval_stddev_ms": round(statistics.pstdev(positive) * 1000, 3),
                "jitter_from_requested_period_ms": round(
                    statistics.mean(abs(value - expected_s) for value in positive) * 1000, 3
                ),
                "intervals_over_100ms": sum(
                    value > self.config.GAP_WARNING_S for value in intervals
                ),
                "intervals_over_500ms": sum(
                    value > self.config.GAP_CRITICAL_S for value in intervals
                ),
                "monotonic": all(value > 0 for value in intervals),
                "nonpositive_intervals": sum(value <= 0 for value in intervals),
                "first_to_last_span_s": round((times[-1] - times[0]) / 1e9, 6),
            }

        sensor = interval_stats("sensor_timestamp_ns")
        host = interval_stats("host_receive_monotonic_ns")
        status = "REVIEW_REQUIRED"
        if (
            sensor.get("monotonic", False) and host.get("monotonic", False)
            and sensor.get("intervals_over_500ms", 0) == 0
            and host.get("intervals_over_500ms", 0) == 0
        ):
            status = "CAPTURE_REVIEWED_NO_CRITICAL_GAPS"

        return {
            "status": status,
            "sample_count": len(rows),
            "observed_message_rate_hz": (
                round((len(rows) - 1) / elapsed_s, 3) if elapsed_s > 0 else 0
            ),
            "sensor_timestamp": sensor,
            "host_arrival_timestamp": host,
        }

    def analyze_timestamps(self, measurements, elapsed_s):
        report = {
            "status": "REVIEW_REQUIRED",
            "elapsed_s": round(elapsed_s, 6),
            "requested_rate_hz": self.config.REQUESTED_RATE_HZ,
            "topics": {
                "rgb": self.config.RGB_TOPIC,
                "depth": self.config.DEPTH_TOPIC,
            },
            "streams": {},
            "note": (
                "ROS header timestamps and Jetson host-arrival timestamps are recorded "
                "separately. This report does not establish clock synchronization or "
                "exact sensor exposure time."
            ),
        }

        for stream in ("rgb", "depth"):
            rows = [row for row in measurements if row["stream"] == stream]
            result = self.analyze_one_stream(rows, elapsed_s)
            report["streams"][stream] = result
            if result.get("status") != "CAPTURE_REVIEWED_NO_CRITICAL_GAPS":
                report["status"] = "REVIEW_REQUIRED"

        if all(
            report["streams"][stream].get("status") == "CAPTURE_REVIEWED_NO_CRITICAL_GAPS"
            for stream in ("rgb", "depth")
        ):
            report["status"] = "CAPTURE_REVIEWED_NO_CRITICAL_GAPS"
        return report

    # Save raw measurements
    def write_csv(self, measurements, output_dir):
        path = output_dir / "raw_measurements.csv"
        fields = [
            "stream", "sample_index", "sensor_timestamp_ns",
            "host_receive_monotonic_ns", "header_frame_id"
        ]
        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(measurements)
        print("Raw data saved:", path)

    # Write timing report
    def write_report(self, report, output_dir):
        json_path = output_dir / "timing_report.json"
        with json_path.open("w", encoding="utf-8") as file:
            json.dump(report, file, indent=2)

        summary_path = output_dir / "summary.txt"
        with summary_path.open("w", encoding="utf-8") as file:
            file.write("REALSENSE D455 TIMING CHARACTERIZATION\n")
            file.write("======================================\n")
            file.write(f"Status: {report['status']}\n")
            file.write(f"Elapsed: {report['elapsed_s']} seconds\n")
            file.write(f"Requested rate: {report['requested_rate_hz']} Hz\n\n")
            for name, stream in report["streams"].items():
                file.write(f"{name.upper()} STREAM\n")
                file.write(f"Samples: {stream['sample_count']}\n")
                file.write(f"Observed rate: {stream.get('observed_message_rate_hz', 'N/A')} Hz\n")
                file.write(f"Status: {stream['status']}\n")
                for key in ("sensor_timestamp", "host_arrival_timestamp"):
                    stats = stream.get(key, {})
                    file.write(
                        f"{key}: monotonic={stats.get('monotonic', 'N/A')}, "
                        f"mean_interval_ms={stats.get('mean_interval_ms', 'N/A')}, "
                        f"max_interval_ms={stats.get('max_interval_ms', 'N/A')}, "
                        f"gaps_over_100ms={stats.get('intervals_over_100ms', 'N/A')}, "
                        f"gaps_over_500ms={stats.get('intervals_over_500ms', 'N/A')}\n"
                    )
                file.write("\n")
            file.write(
                "Header and host-arrival timestamps are separate measurements; "
                "this report does not prove clock synchronization.\n"
            )
        print("JSON report saved:", json_path)
        print("Summary saved:", summary_path)

    # Complete workflow
    def run(self):
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = self.config.OUTPUT_ROOT / run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        measurements, elapsed_s = self.capture_measurements()
        self.write_csv(measurements, output_dir)
        report = self.analyze_timestamps(measurements, elapsed_s)
        self.write_report(report, output_dir)

        print("\nRealSense timing characterization finished.")
        print("Output directory:", output_dir)


def main():
    rclpy.init()
    config = Configuration()
    logic = Logic(config)
    try:
        logic.run()
    except KeyboardInterrupt:
        print("\nTiming test interrupted by user.")
    except Exception as exc:
        print(f"Timing test failed: {type(exc).__name__}: {exc}")
        raise
    finally:
        logic.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()