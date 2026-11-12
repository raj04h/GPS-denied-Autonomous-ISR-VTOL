
#!/usr/bin/env python3
"""Analyze Strix IMU and RealSense timing logs without altering raw data.

SM-02A:
    Analyze standalone Strix and RealSense timing logs.

SM-02B:
    Associate RGB and depth frames from an existing concurrent capture
    using header_stamp_ns and a provisional 10 ms tolerance.
"""

# 1. IMPORTS
import argparse
import csv
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path


# 2. CONFIGURATION
class Configuration:
    PROJECT_DATA = Path.home() / "strix_timing_data"
    STRIX_CSV = PROJECT_DATA / "20261026_211803" / "raw_measurements.csv"
    REALSENSE_CSV = (
        PROJECT_DATA / "realsense" / "20261026_211906" / "raw_measurements.csv"
    )
    OUTPUT_ROOT = PROJECT_DATA / "timing_analysis"

    REQUESTED_RATES_HZ = {
        "strix": 50,
        "rgb": 30,
        "depth": 30,
    }

    GAP_WARNING_S = 0.100
    GAP_CRITICAL_S = 0.500

    # SM-02B provisional association tolerance.
    SM02B_TOLERANCE_NS = 10_000_000


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

        # Long intervals remain in the report but are excluded from
        # nominal-rate statistics.
        gap_limit_s = max(
            3.0 * expected_s,
            Configuration.GAP_WARNING_S,
        )

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

        positive = [value for value in intervals_s if value > 0]
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
            "nonpositive_intervals": sum(
                value <= 0 for value in intervals_s
            ),
            "monotonic": all(value > 0 for value in intervals_s),
            "intervals_over_100ms": sum(
                value > Configuration.GAP_WARNING_S
                for value in intervals_s
            ),
            "intervals_over_500ms": sum(
                value > Configuration.GAP_CRITICAL_S
                for value in intervals_s
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
            result["max_interval_ms"] = round(
                max(intervals_s) * 1000, 3
            )

        return result

    def analyze_strix(self, path):
        rows = self.read_csv(path)

        required = {
            "sensor_time_usec",
            "host_receive_monotonic_ns",
        }

        if not rows or not required.issubset(rows[0]):
            raise ValueError(
                f"Unexpected Strix CSV schema: {path}"
            )

        sensor_ns = [
            int(row["sensor_time_usec"]) * 1000
            for row in rows
        ]
        host_ns = [
            int(row["host_receive_monotonic_ns"])
            for row in rows
        ]

        return {
            "source_file": str(path),
            "sensor_timestamp": self.interval_analysis(
                sensor_ns,
                self.config.REQUESTED_RATES_HZ["strix"],
            ),
            "host_arrival_timestamp": self.interval_analysis(
                host_ns,
                self.config.REQUESTED_RATES_HZ["strix"],
            ),
        }

    def analyze_realsense(self, path):
        """Existing SM-02A analysis of the standalone RealSense CSV."""
        rows = self.read_csv(path)

        required = {
            "stream",
            "sensor_timestamp_ns",
            "host_receive_monotonic_ns",
        }

        if not rows or not required.issubset(rows[0]):
            raise ValueError(
                f"Unexpected RealSense CSV schema: {path}"
            )

        streams = {}

        for name in ("rgb", "depth"):
            selected = sorted(
                (
                    row for row in rows
                    if row["stream"] == name
                ),
                key=lambda row: int(row["sample_index"]),
            )

            if not selected:
                streams[name] = {
                    "status": "NO_SAMPLES",
                    "sample_count": 0,
                }
                continue

            streams[name] = {
                "sensor_timestamp": self.interval_analysis(
                    [
                        row["sensor_timestamp_ns"]
                        for row in selected
                    ],
                    self.config.REQUESTED_RATES_HZ[name],
                ),
                "host_arrival_timestamp": self.interval_analysis(
                    [
                        row["host_receive_monotonic_ns"]
                        for row in selected
                    ],
                    self.config.REQUESTED_RATES_HZ[name],
                ),
            }

        # Preserve the existing SM-02A pairing behavior for this
        # separate capture. SM-02B uses its own concurrent-data method.
        rgb = sorted(
            (
                row for row in rows
                if row["stream"] == "rgb"
            ),
            key=lambda row: int(row["sensor_timestamp_ns"]),
        )
        depth = sorted(
            (
                row for row in rows
                if row["stream"] == "depth"
            ),
            key=lambda row: int(row["sensor_timestamp_ns"]),
        )

        rgb_times = [
            int(row["sensor_timestamp_ns"])
            for row in rgb
        ]
        depth_times = [
            int(row["sensor_timestamp_ns"])
            for row in depth
        ]

        tolerance_ns = int(
            0.5 * 1e9
            / self.config.REQUESTED_RATES_HZ["rgb"]
        )

        i = j = 0
        pair_deltas_ms = []
        unmatched_rgb = 0
        unmatched_depth = 0

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

        absolute_offsets = sorted(
            abs(value) for value in pair_deltas_ms
        )

        return {
            "source_file": str(path),
            "streams": streams,
            "rgb_depth_timestamp_comparison": {
                "method": (
                    "one-to-one timestamp pairing within half "
                    "a nominal RGB frame period"
                ),
                "pair_tolerance_ms": round(
                    tolerance_ns / 1e6, 3
                ),
                "rgb_count": len(rgb_times),
                "depth_count": len(depth_times),
                "paired_count": len(pair_deltas_ms),
                "unmatched_rgb_count": unmatched_rgb,
                "unmatched_depth_count": unmatched_depth,
                "median_signed_offset_ms": (
                    round(statistics.median(pair_deltas_ms), 4)
                    if pair_deltas_ms else None
                ),
                "median_absolute_offset_ms": (
                    round(
                        statistics.median(absolute_offsets), 4
                    )
                    if absolute_offsets else None
                ),
                "p95_absolute_offset_ms": (
                    round(
                        absolute_offsets[
                            min(
                                len(absolute_offsets) - 1,
                                math.ceil(
                                    0.95 * len(absolute_offsets)
                                ) - 1,
                            )
                        ],
                        4,
                    )
                    if absolute_offsets else None
                ),
                "note": (
                    "Timestamp pairing is diagnostic, not proof "
                    "of matching exposure time. Verify timestamp "
                    "domains and frame metadata before treating "
                    "these offsets as synchronization accuracy."
                ),
            },
        }

    # ---------------------------------------------------------
    # SM-02B: CONCURRENT RGB-DEPTH ASSOCIATION
    # ---------------------------------------------------------
    @staticmethod
    def _load_concurrent_stream(path):
        """Load original rows without sorting or modifying timestamps."""
        with path.open(
            "r",
            newline="",
            encoding="utf-8",
        ) as file:
            rows = list(csv.DictReader(file))

        required = {
            "sample_index",
            "header_stamp_ns",
        }

        if not rows or not required.issubset(rows[0]):
            raise ValueError(
                f"Unexpected or empty concurrent CSV schema: {path}. "
                f"Required columns: {sorted(required)}"
            )

        for row in rows:
            row["sample_index"] = int(row["sample_index"])
            row["header_stamp_ns"] = int(
                row["header_stamp_ns"]
            )

        timestamps = [
            row["header_stamp_ns"] for row in rows
        ]

        validation = {
            "file": str(path),
            "sample_count": len(rows),
            "strictly_increasing": all(
                current > previous
                for previous, current in zip(
                    timestamps, timestamps[1:]
                )
            ),
            "nondecreasing": all(
                current >= previous
                for previous, current in zip(
                    timestamps, timestamps[1:]
                )
            ),
            "duplicate_adjacent_timestamp_count": sum(
                current == previous
                for previous, current in zip(
                    timestamps, timestamps[1:]
                )
            ),
            "timestamp_regression_count": sum(
                current < previous
                for previous, current in zip(
                    timestamps, timestamps[1:]
                )
            ),
        }

        return rows, validation

    @staticmethod
    def _associate_monotonic(rgb, depth, tolerance_ns):
        """Maximize valid monotonic pairs, then minimize total offset."""
        n = len(rgb)
        m = len(depth)

        # DP objective:
        # 1. Maximize the number of pairs within tolerance.
        # 2. Minimize their total absolute timestamp difference.
        #
        # Inputs must already be strictly monotonic. No sorting is done.
        pair_count = [
            [0] * (m + 1)
            for _ in range(n + 1)
        ]
        total_cost = [
            [0] * (m + 1)
            for _ in range(n + 1)
        ]
        choice = [
            bytearray(m + 1)
            for _ in range(n + 1)
        ]

        # Choices: 1 = skip RGB, 2 = skip depth, 3 = match.
        for i in range(1, n + 1):
            choice[i][0] = 1

        for j in range(1, m + 1):
            choice[0][j] = 2

        for i in range(1, n + 1):
            rgb_time = rgb[i - 1]["header_stamp_ns"]

            for j in range(1, m + 1):
                best_pairs = pair_count[i - 1][j]
                best_cost = total_cost[i - 1][j]
                best_choice = 1

                # Option 2: skip current depth frame.
                candidate_pairs = pair_count[i][j - 1]
                candidate_cost = total_cost[i][j - 1]

                if (
                    candidate_pairs > best_pairs
                    or (
                        candidate_pairs == best_pairs
                        and candidate_cost < best_cost
                    )
                ):
                    best_pairs = candidate_pairs
                    best_cost = candidate_cost
                    best_choice = 2

                # Option 3: match these two frames.
                depth_time = depth[j - 1]["header_stamp_ns"]
                delta_ns = abs(rgb_time - depth_time)

                if delta_ns <= tolerance_ns:
                    candidate_pairs = (
                        pair_count[i - 1][j - 1] + 1
                    )
                    candidate_cost = (
                        total_cost[i - 1][j - 1] + delta_ns
                    )

                    if (
                        candidate_pairs > best_pairs
                        or (
                            candidate_pairs == best_pairs
                            and candidate_cost < best_cost
                        )
                    ):
                        best_pairs = candidate_pairs
                        best_cost = candidate_cost
                        best_choice = 3

                pair_count[i][j] = best_pairs
                total_cost[i][j] = best_cost
                choice[i][j] = best_choice

        pairs = []
        unmatched_rgb = []
        unmatched_depth = []

        i, j = n, m

        while i > 0 or j > 0:
            selected = choice[i][j]

            if i > 0 and j > 0 and selected == 3:
                pairs.append((rgb[i - 1], depth[j - 1]))
                i -= 1
                j -= 1
            elif i > 0 and (
                j == 0 or selected == 1
            ):
                unmatched_rgb.append(rgb[i - 1])
                i -= 1
            else:
                unmatched_depth.append(depth[j - 1])
                j -= 1

        pairs.reverse()
        unmatched_rgb.reverse()
        unmatched_depth.reverse()

        return pairs, unmatched_rgb, unmatched_depth

    @staticmethod
    def _percentile(values, percentile):
        """Linearly interpolated percentile for a sorted or unsorted list."""
        if not values:
            return None

        ordered = sorted(values)
        position = (len(ordered) - 1) * percentile
        lower = math.floor(position)
        upper = math.ceil(position)

        if lower == upper:
            return ordered[lower]

        return (
            ordered[lower] * (upper - position)
            + ordered[upper] * (position - lower)
        )

    def analyze_concurrent_rgb_depth(self, data_dir):
        """Run SM-02B against the existing concurrent capture directory."""
        data_dir = Path(data_dir)

        rgb_path = data_dir / "rgb_timing.csv"
        depth_path = data_dir / "depth_timing.csv"

        if not rgb_path.is_file():
            raise FileNotFoundError(
                f"RGB timing CSV not found: {rgb_path}"
            )

        if not depth_path.is_file():
            raise FileNotFoundError(
                f"Depth timing CSV not found: {depth_path}"
            )

        tolerance_ns = self.config.SM02B_TOLERANCE_NS
        output_dir = data_dir / "sm02b_association_10ms"

        rgb, rgb_validation = self._load_concurrent_stream(
            rgb_path
        )
        depth, depth_validation = self._load_concurrent_stream(
            depth_path
        )

        # Do not silently sort, repair, or alter the original sequence.
        if not rgb_validation["strictly_increasing"]:
            raise ValueError(
                "SM-02B stopped: RGB header timestamps are not "
                "strictly increasing. Inspect the RGB validation "
                f"data: {rgb_validation}"
            )

        if not depth_validation["strictly_increasing"]:
            raise ValueError(
                "SM-02B stopped: depth header timestamps are not "
                "strictly increasing. Inspect the depth validation "
                f"data: {depth_validation}"
            )

        pairs, unmatched_rgb, unmatched_depth = (
            self._associate_monotonic(
                rgb,
                depth,
                tolerance_ns,
            )
        )

        signed_ms = [
            (
                rgb_row["header_stamp_ns"]
                - depth_row["header_stamp_ns"]
            ) / 1e6
            for rgb_row, depth_row in pairs
        ]

        absolute_ms = [
            abs(value) for value in signed_ms
        ]

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        # Matched pairs: retain both original header timestamps.
        matched_path = output_dir / "matched_pairs.csv"

        matched_fields = [
            "rgb_sample_index",
            "rgb_header_stamp_ns",
            "depth_sample_index",
            "depth_header_stamp_ns",
            "signed_delta_ms",
            "absolute_delta_ms",
        ]

        with matched_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=matched_fields,
            )
            writer.writeheader()

            for rgb_row, depth_row in pairs:
                delta_ms = (
                    rgb_row["header_stamp_ns"]
                    - depth_row["header_stamp_ns"]
                ) / 1e6

                writer.writerow({
                    "rgb_sample_index": rgb_row["sample_index"],
                    "rgb_header_stamp_ns": (
                        rgb_row["header_stamp_ns"]
                    ),
                    "depth_sample_index": (
                        depth_row["sample_index"]
                    ),
                    "depth_header_stamp_ns": (
                        depth_row["header_stamp_ns"]
                    ),
                    "signed_delta_ms": delta_ms,
                    "absolute_delta_ms": abs(delta_ms),
                })

        # Explicit unmatched-frame accounting.
        unmatched_path = output_dir / "unmatched_frames.csv"

        with unmatched_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            fields = [
                "stream",
                "sample_index",
                "header_stamp_ns",
            ]
            writer = csv.DictWriter(
                file,
                fieldnames=fields,
            )
            writer.writeheader()

            for row in unmatched_rgb:
                writer.writerow({
                    "stream": "rgb",
                    "sample_index": row["sample_index"],
                    "header_stamp_ns": row["header_stamp_ns"],
                })

            for row in unmatched_depth:
                writer.writerow({
                    "stream": "depth",
                    "sample_index": row["sample_index"],
                    "header_stamp_ns": row["header_stamp_ns"],
                })

        accounting_valid = (
            len(pairs) + len(unmatched_rgb) == len(rgb)
            and len(pairs) + len(unmatched_depth) == len(depth)
        )

        all_pairs_within_tolerance = all(
            value <= tolerance_ns / 1e6
            for value in absolute_ms
        )

        association_valid = (
            rgb_validation["strictly_increasing"]
            and depth_validation["strictly_increasing"]
            and accounting_valid
            and all_pairs_within_tolerance
        )

        summary = {
            "step": "SM-02B",
            "created_at_utc": datetime.now(
                timezone.utc
            ).isoformat(),
            "input_directory": str(data_dir),
            "timestamp_field": "header_stamp_ns",
            "tolerance_ms": tolerance_ns / 1e6,
            "association_method": (
                "Monotonic one-to-one association; maximize the "
                "number of pairs within tolerance, then minimize "
                "total absolute timestamp difference."
            ),
            "rgb_count": len(rgb),
            "depth_count": len(depth),
            "accepted_pairs": len(pairs),
            "unmatched_rgb_count": len(unmatched_rgb),
            "unmatched_depth_count": len(unmatched_depth),
            "rgb_validation": rgb_validation,
            "depth_validation": depth_validation,
            "timestamp_difference_ms": {
                "signed_median": (
                    statistics.median(signed_ms)
                    if signed_ms else None
                ),
                "absolute_median": (
                    statistics.median(absolute_ms)
                    if absolute_ms else None
                ),
                "absolute_p95": self._percentile(
                    absolute_ms, 0.95
                ),
                "absolute_max": (
                    max(absolute_ms)
                    if absolute_ms else None
                ),
                "absolute_min": (
                    min(absolute_ms)
                    if absolute_ms else None
                ),
                "absolute_mean": (
                    statistics.mean(absolute_ms)
                    if absolute_ms else None
                ),
            },
            "pair_count_reconciles": accounting_valid,
            "all_pairs_within_tolerance": (
                all_pairs_within_tolerance
            ),
            "association_valid": association_valid,
            "original_timestamps_preserved": True,
            "hardware_exposure_sync_proven": False,
            "limitations": [
                (
                    "Header timestamp association does not prove "
                    "hardware exposure synchronization."
                ),
                (
                    "Timestamp clock-domain and exposure-time "
                    "semantics are not established by SM-02B."
                ),
                (
                    "Unmatched frames are explicitly retained in "
                    "unmatched_frames.csv."
                ),
            ],
        }

        summary_path = output_dir / "summary.json"
        summary_path.write_text(
            json.dumps(summary, indent=2) + "\n",
            encoding="utf-8",
        )

        print("\n=== SM-02B RESULTS ===")
        print(f"RGB samples:              {len(rgb)}")
        print(f"Depth samples:            {len(depth)}")
        print(f"Tolerance:                {tolerance_ns / 1e6:.3f} ms")
        print(f"Accepted pairs:           {len(pairs)}")
        print(f"Unmatched RGB:            {len(unmatched_rgb)}")
        print(f"Unmatched depth:          {len(unmatched_depth)}")
        print(
            "RGB strictly increasing:  "
            f"{rgb_validation['strictly_increasing']}"
        )
        print(
            "Depth strictly increasing: "
            f"{depth_validation['strictly_increasing']}"
        )
        print(f"Pair accounting valid:    {accounting_valid}")
        print(
            "All pairs within tolerance: "
            f"{all_pairs_within_tolerance}"
        )
        print(f"Association valid:        {association_valid}")
        print(f"Matched pairs:            {matched_path}")
        print(f"Unmatched frames:         {unmatched_path}")
        print(f"Summary:                  {summary_path}")

        return summary

    # ---------------------------------------------------------
    # EXISTING SM-02A ENTRY POINT — PRESERVED
    # ---------------------------------------------------------
    def run(self, strix_path, realsense_path):
        if not strix_path.is_file():
            raise FileNotFoundError(
                f"Strix CSV not found: {strix_path}"
            )

        if not realsense_path.is_file():
            raise FileNotFoundError(
                f"RealSense CSV not found: {realsense_path}"
            )

        report = {
            "created_at": datetime.now().isoformat(
                timespec="seconds"
            ),
            "purpose": (
                "Timing characterization and synchronization readiness"
            ),
            "strix": self.analyze_strix(strix_path),
            "realsense": self.analyze_realsense(realsense_path),
            "cross_sensor_sync": {
                "status": (
                    "NOT_ESTIMATED_FROM_SEPARATE_CAPTURE_SESSIONS"
                ),
                "reason": (
                    "The Strix and standalone RealSense logs are "
                    "independent captures. Per-stream rates and host "
                    "arrival intervals can be characterized, but these "
                    "logs do not establish simultaneous IMU-camera "
                    "timing, sensor clock offset, or drift."
                ),
            },
        }

        self.config.OUTPUT_ROOT.mkdir(
            parents=True,
            exist_ok=True,
        )

        json_path = (
            self.config.OUTPUT_ROOT
            / "cross_sensor_timing_report.json"
        )

        json_path.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )

        summary_path = (
            self.config.OUTPUT_ROOT
            / "cross_sensor_timing_summary.txt"
        )

        summary_path.write_text(
            "CROSS-SENSOR TIMING ANALYSIS\n"
            "============================\n"
            f"Strix samples: "
            f"{report['strix']['sensor_timestamp']['sample_count']}\n"
            "RGB samples: "
            f"{report['realsense']['streams']['rgb'].get('sensor_timestamp', {}).get('sample_count', 0)}\n"
            "Depth samples: "
            f"{report['realsense']['streams']['depth'].get('sensor_timestamp', {}).get('sample_count', 0)}\n"
            "RGB-depth analysis: "
            f"{report['realsense']['rgb_depth_timestamp_comparison']['method']}\n"
            "IMU-camera offset/drift: NOT ESTIMATED "
            "(independent captures)\n"
            "Review JSON for detailed interval, gap, and timestamp results.\n",
            encoding="utf-8",
        )

        print("Timing analysis complete.")
        print("JSON report:", json_path)
        print("Summary:", summary_path)


# 4. EXECUTION
def main():
    parser = argparse.ArgumentParser(
        description="Analyze Strix and RealSense timing logs."
    )

    parser.add_argument(
        "--strix",
        type=Path,
        default=Configuration.STRIX_CSV,
    )

    parser.add_argument(
        "--realsense",
        type=Path,
        default=Configuration.REALSENSE_CSV,
    )

    parser.add_argument(
        "--sm02b-concurrent",
        type=Path,
        default=None,
        help=(
            "Run SM-02B using an existing concurrent capture "
            "directory containing rgb_timing.csv and depth_timing.csv."
        ),
    )

    args = parser.parse_args()

    try:
        logic = Logic(Configuration())

        if args.sm02b_concurrent is not None:
            logic.analyze_concurrent_rgb_depth(
                args.sm02b_concurrent
            )
        else:
            logic.run(
                args.strix,
                args.realsense,
            )

    except Exception as exc:
        raise SystemExit(
            f"Timing analysis failed: {type(exc).__name__}: {exc}"
        )


if __name__ == "__main__":
    main()
