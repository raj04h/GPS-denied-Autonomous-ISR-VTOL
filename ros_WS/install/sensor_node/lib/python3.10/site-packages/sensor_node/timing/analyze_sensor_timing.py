"""Analyze Strix IMU and RealSense timing logs without altering raw data."""

# 1. IMPORTS
import argparse
import csv
import json
import statistics
from datetime import datetime
from pathlib import Path


# 2. CONFIGURATION
class Configuration:
    PROJECT_DATA = Path.home() / "strix_timing_data"
    STRIX_CSV = PROJECT_DATA / "20261026_211803" / "raw_measurements.csv"
    REALSENSE_CSV = PROJECT_DATA / "realsense" / "20261026_211906" / "raw_measurements.csv"
    OUTPUT_ROOT = PROJECT_DATA / "timing_analysis"
    REQUESTED_RATES_HZ = {"strix": 50, "rgb": 30, "depth": 30}
    GAP_WARNING_S = 0.100
    GAP_CRITICAL_S = 0.500

# 3. CORE LOGIC
class Logic:
    def __init__(self, config):
        self.config = config

    @staticmethod
    def read_csv(path):
        with path.open("r", newline="", encoding="utf-8") as file:
            return list(csv.DictReader(file))

    @staticmethod
    def interval_analysis(values_ns, requested_rate_hz):
        values = [int(value) for value in values_ns]

        if len(values) < 2:
            return {
                "sample_count": len(values),
                "status": "INSUFFICIENT_DATA",
            }

        intervals_s = [
            (values[i] - values[i - 1]) / 1e9
            for i in range(1, len(values))
        ]

        expected_s = 1.0 / requested_rate_hz
        # Intervals longer than three nominal periods are treated as gaps.
        # They remain in the report but are excluded from nominal-rate stats.
        gap_limit_s = max(3.0 * expected_s, Configuration.GAP_WARNING_S)

        anomalies = []
        valid_intervals = []

        for i, interval_s in enumerate(intervals_s):
            if interval_s <= 0:
                anomalies.append({
                    "previous_sample_index": i + 1,
                    "current_sample_index": i + 2,
                    "interval_ms": round(interval_s * 1000, 3),
                    "reason": "NONPOSITIVE_INTERVAL",
                })
            elif interval_s > gap_limit_s:
                anomalies.append({
                    "previous_sample_index": i + 1,
                    "current_sample_index": i + 2,
                    "interval_ms": round(interval_s * 1000, 3),
                    "reason": "LONG_INTERVAL",
                })
            else:
                valid_intervals.append(interval_s)

        positive = [x for x in intervals_s if x > 0]
        span_s = (values[-1] - values[0]) / 1e9
        status = (
            "REVIEW_REQUIRED"
            if anomalies or not positive
            else "OK"
        )

        result = {
            "sample_count": len(values),
            "span_s": round(span_s, 6),
            "requested_rate_hz": requested_rate_hz,
            "status": status,
            "gap_limit_ms": round(gap_limit_s * 1000, 3),
            "total_interval_count": len(intervals_s),
            "valid_interval_count": len(valid_intervals),
            "anomaly_count": len(anomalies),
            "anomalies": anomalies,
            "nonpositive_intervals": sum(x <= 0 for x in intervals_s),
            "monotonic": all(x > 0 for x in intervals_s),
            "intervals_over_100ms": sum(
                x > Configuration.GAP_WARNING_S for x in intervals_s
            ),
            "intervals_over_500ms": sum(
                x > Configuration.GAP_CRITICAL_S for x in intervals_s
            ),
        }

        if valid_intervals:
            median_s = statistics.median(valid_intervals)
            result.update({
                "observed_rate_hz": round(1.0 / median_s, 3),
                "valid_interval_rate_hz": round(
                    len(valid_intervals) / sum(valid_intervals), 3
                ),
                "mean_interval_ms": round(
                    statistics.mean(valid_intervals) * 1000, 3
                ),
                "median_interval_ms": round(median_s * 1000, 3),
                "min_positive_interval_ms": round(
                    min(valid_intervals) * 1000, 3
                ),
                "max_valid_interval_ms": round(
                    max(valid_intervals) * 1000, 3
                ),
                "interval_stddev_ms": round(
                    statistics.pstdev(valid_intervals) * 1000, 3
                ),
            })
        else:
            result["observed_rate_hz"] = None
            result["valid_interval_rate_hz"] = None

        if positive:
            result["max_interval_ms"] = round(max(intervals_s) * 1000, 3)

        return result

    def analyze_strix(self, path):
        rows = self.read_csv(path)
        required = {"sensor_time_usec", "host_receive_monotonic_ns"}
        if not rows or not required.issubset(rows[0]):
            raise ValueError(f"Unexpected Strix CSV schema: {path}")

        sensor_ns = [int(row["sensor_time_usec"]) * 1000 for row in rows]
        host_ns = [int(row["host_receive_monotonic_ns"]) for row in rows]
        return {
            "source_file": str(path),
            "sensor_timestamp": self.interval_analysis(
                sensor_ns, self.config.REQUESTED_RATES_HZ["strix"]
            ),
            "host_arrival_timestamp": self.interval_analysis(
                host_ns, self.config.REQUESTED_RATES_HZ["strix"]
            ),
        }

    def analyze_realsense(self, path):
        rows = self.read_csv(path)
        required = {
            "stream", "sensor_timestamp_ns", "host_receive_monotonic_ns"
        }
        if not rows or not required.issubset(rows[0]):
            raise ValueError(f"Unexpected RealSense CSV schema: {path}")

        streams = {}
        for name in ("rgb", "depth"):
            selected = sorted(
                (row for row in rows if row["stream"] == name),
                key=lambda row: int(row["sample_index"]),
            )
            if not selected:
                streams[name] = {"status": "NO_SAMPLES", "sample_count": 0}
                continue
            streams[name] = {
                "sensor_timestamp": self.interval_analysis(
                    [row["sensor_timestamp_ns"] for row in selected],
                    self.config.REQUESTED_RATES_HZ[name],
                ),
                "host_arrival_timestamp": self.interval_analysis(
                    [row["host_receive_monotonic_ns"] for row in selected],
                    self.config.REQUESTED_RATES_HZ[name],
                ),
            }

        rgb = sorted(
            (row for row in rows if row["stream"] == "rgb"),
            key=lambda row: int(row["sensor_timestamp_ns"]),
        )
        depth = sorted(
            (row for row in rows if row["stream"] == "depth"),
            key=lambda row: int(row["sensor_timestamp_ns"]),
        )
        rgb_times = [int(row["sensor_timestamp_ns"]) for row in rgb]
        depth_times = [int(row["sensor_timestamp_ns"]) for row in depth]
        # Greedy one-to-one pairing. A half-frame-period tolerance avoids
        # pairing frames across a full missing-frame interval.
        tolerance_ns = int(0.5 * 1e9 / self.config.REQUESTED_RATES_HZ["rgb"])
        i = j = 0
        pair_deltas_ms = []
        unmatched_rgb = unmatched_depth = 0
        while i < len(rgb_times) and j < len(depth_times):
            delta_ns = rgb_times[i] - depth_times[j]
            if abs(delta_ns) <= tolerance_ns:
                pair_deltas_ms.append(delta_ns / 1e6)
                i += 1
                j += 1
            elif delta_ns < 0:
                unmatched_rgb += 1
                i += 1
            else:
                unmatched_depth += 1
                j += 1
        unmatched_rgb += len(rgb_times) - i
        unmatched_depth += len(depth_times) - j

        absolute_offsets = sorted(abs(value) for value in pair_deltas_ms)
        return {
            "source_file": str(path),
            "streams": streams,
            "rgb_depth_timestamp_comparison": {
                "method": "one-to-one timestamp pairing within half a nominal RGB frame period",
                "pair_tolerance_ms": round(tolerance_ns / 1e6, 3),
                "rgb_count": len(rgb_times),
                "depth_count": len(depth_times),
                "paired_count": len(pair_deltas_ms),
                "unmatched_rgb_count": unmatched_rgb,
                "unmatched_depth_count": unmatched_depth,
                "median_signed_offset_ms": round(statistics.median(pair_deltas_ms), 4)
                    if pair_deltas_ms else None,
                "median_absolute_offset_ms": round(
                    statistics.median(absolute_offsets), 4
                ) if absolute_offsets else None,
                "p95_absolute_offset_ms": round(
                    absolute_offsets[min(len(absolute_offsets) - 1,
                                          int(0.95 * len(absolute_offsets)))], 4
                ) if absolute_offsets else None,
                "note": (
                    "Timestamp pairing is diagnostic, not proof of matching exposure time. "
                    "Verify timestamp domains and frame metadata before treating these "
                    "offsets as synchronization accuracy."
                ),
            },
        }

    def run(self, strix_path, realsense_path):
        if not strix_path.is_file():
            raise FileNotFoundError(f"Strix CSV not found: {strix_path}")
        if not realsense_path.is_file():
            raise FileNotFoundError(f"RealSense CSV not found: {realsense_path}")

        report = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "purpose": "Timing characterization and synchronization readiness",
            "strix": self.analyze_strix(strix_path),
            "realsense": self.analyze_realsense(realsense_path),
            "cross_sensor_sync": {
                "status": "NOT_ESTIMATED_FROM_SEPARATE_CAPTURE_SESSIONS",
                "reason": (
                    "The uploaded Strix and RealSense logs are independent captures. "
                    "Per-stream rates and host arrival intervals can be characterized, "
                    "but these logs do not establish simultaneous IMU-camera timing, "
                    "sensor clock offset, or drift. Capture both streams concurrently "
                    "with a shared timing reference or validated clock mapping."
                ),
            },
        }

        self.config.OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        json_path = self.config.OUTPUT_ROOT / "cross_sensor_timing_report.json"
        json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        summary_path = self.config.OUTPUT_ROOT / "cross_sensor_timing_summary.txt"
        summary_path.write_text(
            "CROSS-SENSOR TIMING ANALYSIS\n"
            "============================\n"
            f"Strix samples: {report['strix']['sensor_timestamp']['sample_count']}\n"
            f"RGB samples: {report['realsense']['streams']['rgb'].get('sensor_timestamp', {}).get('sample_count', 0)}\n"
            f"Depth samples: {report['realsense']['streams']['depth'].get('sensor_timestamp', {}).get('sample_count', 0)}\n"
            f"RGB-depth analysis: {report['realsense']['rgb_depth_timestamp_comparison']['method']}\n"
            "IMU-camera offset/drift: NOT ESTIMATED (independent captures)\n"
            "Review JSON for detailed interval, gap, and timestamp results.\n",
            encoding="utf-8",
        )
        print("Timing analysis complete.")
        print("JSON report:", json_path)
        print("Summary:", summary_path)


# 4. EXECUTION
# 4. EXECUTION
def main():
    parser = argparse.ArgumentParser(
        description="Analyze Strix and RealSense timing logs."
    )
    parser.add_argument(
        "--strix", type=Path, default=Configuration.STRIX_CSV
    )
    parser.add_argument(
        "--realsense", type=Path, default=Configuration.REALSENSE_CSV
    )
    args = parser.parse_args()

    try:
        Logic(Configuration()).run(args.strix, args.realsense)
    except Exception as exc:
        raise SystemExit(
            f"Timing analysis failed: {type(exc).__name__}: {exc}"
        )


if __name__ == "__main__":
    main()