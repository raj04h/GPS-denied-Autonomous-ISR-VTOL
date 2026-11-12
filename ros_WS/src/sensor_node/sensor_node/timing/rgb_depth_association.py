#!/usr/bin/env python3
"""Offline one-to-one RGB/depth timestamp association for ROS timing CSVs.

Expected files:
  rgb_timing.csv   : sample_index, host_callback_monotonic_ns, header_stamp_ns, ...
  depth_timing.csv : sample_index, host_callback_monotonic_ns, header_stamp_ns, ...

The script preserves raw timestamps and never fabricates frames. It assumes RGB
and depth header stamps are comparable only for the purpose of producing a
candidate association report; verify their clock domain and semantics separately.
"""
import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path


def read_rows(path, stream_name):
    with path.open("r", newline="") as f:
        rows = list(csv.DictReader(f))
    required = {"sample_index", "host_callback_monotonic_ns", "header_stamp_ns"}
    if rows and not required.issubset(rows[0].keys()):
        missing = sorted(required - set(rows[0].keys()))
        raise ValueError(f"{path}: missing required columns: {missing}")
    parsed = []
    invalid = 0
    for row_number, row in enumerate(rows, start=2):
        try:
            item = {
                "sample_index": int(row["sample_index"]),
                "host_callback_monotonic_ns": int(row["host_callback_monotonic_ns"]),
                "header_stamp_ns": int(row["header_stamp_ns"]),
            }
            if item["header_stamp_ns"] <= 0:
                invalid += 1
                continue
            parsed.append(item)
        except (ValueError, TypeError, KeyError):
            invalid += 1
    # Check the original CSV order before sorting for association.
    regressions = 0
    previous = None
    for item in parsed:
        stamp = item["header_stamp_ns"]
        if previous is not None and stamp <= previous:
            regressions += 1
        previous = stamp
    # Sorting is for association only; original timestamp values are retained.
    parsed.sort(key=lambda x: (x["header_stamp_ns"], x["sample_index"]))
    return parsed, {"input_rows": len(rows), "invalid_or_zero_timestamps": invalid,
                    "non_increasing_in_input_order": regressions}


def associate(rgb, depth, tolerance_ns):
    """Order-preserving DP: maximize number of pairs, then minimize total |dt|."""
    n, m = len(rgb), len(depth)
    if (n + 1) * (m + 1) > 8_000_000:
        raise ValueError(
            f"Association matrix would be too large ({n}x{m}). "
            "Split the capture into shorter sessions before association."
        )

    # path: 1=skip RGB, 2=skip depth, 3=match. One byte per cell.
    width = m + 1
    path = bytearray((n + 1) * width)

    prev_count = [0] * (m + 1)
    prev_cost = [0] * (m + 1)
    for j in range(1, m + 1):
        path[j] = 2

    for i in range(1, n + 1):
        curr_count = [0] * (m + 1)
        curr_cost = [0] * (m + 1)
        path[i * width] = 1
        rt = rgb[i - 1]["header_stamp_ns"]
        for j in range(1, m + 1):
            # Default: leave this RGB unmatched.
            best_count = prev_count[j]
            best_cost = prev_cost[j]
            best_dir = 1

            # Or leave this depth unmatched.
            c, cost = curr_count[j - 1], curr_cost[j - 1]
            if c > best_count or (c == best_count and cost < best_cost):
                best_count, best_cost, best_dir = c, cost, 2

            # Or match this RGB/depth pair if within tolerance.
            delta = abs(rt - depth[j - 1]["header_stamp_ns"])
            if delta <= tolerance_ns:
                c = prev_count[j - 1] + 1
                cost = prev_cost[j - 1] + delta
                if c > best_count or (c == best_count and cost < best_cost):
                    best_count, best_cost, best_dir = c, cost, 3

            curr_count[j], curr_cost[j] = best_count, best_cost
            path[i * width + j] = best_dir
        prev_count, prev_cost = curr_count, curr_cost

    pairs = []
    matched_rgb, matched_depth = set(), set()
    i, j = n, m
    while i > 0 or j > 0:
        direction = path[i * width + j]
        if i > 0 and j > 0 and direction == 3:
            r, d = rgb[i - 1], depth[j - 1]
            pairs.append((r, d))
            matched_rgb.add(i - 1)
            matched_depth.add(j - 1)
            i -= 1
            j -= 1
        elif i > 0 and (j == 0 or direction == 1):
            i -= 1
        elif j > 0:
            j -= 1
        else:
            break
    pairs.reverse()
    unmatched_rgb = [item for idx, item in enumerate(rgb) if idx not in matched_rgb]
    unmatched_depth = [item for idx, item in enumerate(depth) if idx not in matched_depth]
    return pairs, unmatched_rgb, unmatched_depth


def percentile(values, p):
    if not values:
        return None
    values = sorted(values)
    pos = (len(values) - 1) * p
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return values[lo]
    return values[lo] * (hi - pos) + values[hi] * (pos - lo)


def write_csv(path, fieldnames, rows):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("capture_dir", type=Path, help="Directory containing RGB/depth timing CSVs")
    ap.add_argument("--tolerance-ms", type=float, default=10.0,
                    help="Maximum absolute source-header timestamp difference (default: 10 ms)")
    ap.add_argument("--output-dir", type=Path, default=None,
                    help="Output directory (default: capture_dir/association)")
    args = ap.parse_args()

    if args.tolerance_ms <= 0:
        ap.error("--tolerance-ms must be positive")
    root = args.capture_dir.expanduser().resolve()
    out = (args.output_dir or (root / "association")).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    rgb, rgb_quality = read_rows(root / "rgb_timing.csv", "rgb")
    depth, depth_quality = read_rows(root / "depth_timing.csv", "depth")
    tolerance_ns = int(args.tolerance_ms * 1_000_000)
    pairs, unmatched_rgb, unmatched_depth = associate(rgb, depth, tolerance_ns)

    pair_rows = []
    deltas_ms = []
    for r, d in pairs:
        delta_ms = (r["header_stamp_ns"] - d["header_stamp_ns"]) / 1e6
        deltas_ms.append(abs(delta_ms))
        pair_rows.append({
            "rgb_sample_index": r["sample_index"],
            "depth_sample_index": d["sample_index"],
            "rgb_header_stamp_ns": r["header_stamp_ns"],
            "depth_header_stamp_ns": d["header_stamp_ns"],
            "signed_rgb_minus_depth_ms": f"{delta_ms:.6f}",
            "absolute_delta_ms": f"{abs(delta_ms):.6f}",
            "rgb_host_callback_monotonic_ns": r["host_callback_monotonic_ns"],
            "depth_host_callback_monotonic_ns": d["host_callback_monotonic_ns"],
            "host_callback_delta_ms": f"{(r['host_callback_monotonic_ns'] - d['host_callback_monotonic_ns']) / 1e6:.6f}",
            "within_tolerance": True,
        })

    write_csv(out / "rgb_depth_pairs.csv", [
        "rgb_sample_index", "depth_sample_index", "rgb_header_stamp_ns",
        "depth_header_stamp_ns", "signed_rgb_minus_depth_ms", "absolute_delta_ms",
        "rgb_host_callback_monotonic_ns", "depth_host_callback_monotonic_ns",
        "host_callback_delta_ms", "within_tolerance"
    ], pair_rows)

    unmatched_rows = []
    for stream, rows in (("rgb", unmatched_rgb), ("depth", unmatched_depth)):
        for row in rows:
            unmatched_rows.append({
                "stream": stream,
                "sample_index": row["sample_index"],
                "header_stamp_ns": row["header_stamp_ns"],
                "host_callback_monotonic_ns": row["host_callback_monotonic_ns"],
                "reason": "NO_UNIQUE_COUNTERPART_WITHIN_TOLERANCE",
            })
    write_csv(out / "unmatched_frames.csv", [
        "stream", "sample_index", "header_stamp_ns",
        "host_callback_monotonic_ns", "reason"
    ], unmatched_rows)

    n_rgb, n_depth, n_pairs = len(rgb), len(depth), len(pairs)
    report = {
        "capture_dir": str(root),
        "association_output_dir": str(out),
        "method": "order_preserving_one_to_one_dynamic_programming",
        "timestamp_field": "ROS header_stamp_ns",
        "timestamp_clock_domain_verified": False,
        "tolerance_ms": args.tolerance_ms,
        "rgb": {**rgb_quality, "valid_timestamps": n_rgb,
                "matched": n_pairs, "unmatched": len(unmatched_rgb),
                "match_rate_percent": round(100 * n_pairs / n_rgb, 3) if n_rgb else None},
        "depth": {**depth_quality, "valid_timestamps": n_depth,
                  "matched": n_pairs, "unmatched": len(unmatched_depth),
                  "match_rate_percent": round(100 * n_pairs / n_depth, 3) if n_depth else None},
        "pairs": {
            "count": n_pairs,
            "absolute_delta_ms_median": statistics.median(deltas_ms) if deltas_ms else None,
            "absolute_delta_ms_p95": percentile(deltas_ms, 0.95),
            "absolute_delta_ms_max": max(deltas_ms) if deltas_ms else None,
            "absolute_delta_ms_mean": statistics.mean(deltas_ms) if deltas_ms else None,
        },
        "interpretation_limits": [
            "Association is provisional until RGB and depth header timestamps are confirmed to share a comparable clock domain and timestamp semantics.",
            "A pair within tolerance is not proof of simultaneous exposure or hardware synchronization.",
            "Unmatched frames are retained in unmatched_frames.csv; raw input CSVs are not modified.",
        ],
    }
    (out / "association_report.json").write_text(json.dumps(report, indent=2) + "\n")

    print(f"Capture: {root}")
    print(f"Output:  {out}")
    print(f"RGB valid timestamps:   {n_rgb}")
    print(f"Depth valid timestamps: {n_depth}")
    print(f"Tolerance:              {args.tolerance_ms:.3f} ms")
    print(f"Accepted pairs:         {n_pairs}")
    print(f"RGB unmatched:          {len(unmatched_rgb)}")
    print(f"Depth unmatched:        {len(unmatched_depth)}")
    print(f"RGB match rate:         {report['rgb']['match_rate_percent']}%")
    print(f"Depth match rate:       {report['depth']['match_rate_percent']}%")
    print(f"Abs delta median:       {report['pairs']['absolute_delta_ms_median']:.3f} ms" if deltas_ms else "Abs delta median:       n/a")
    print(f"Abs delta p95:           {report['pairs']['absolute_delta_ms_p95']:.3f} ms" if deltas_ms else "Abs delta p95:           n/a")
    print(f"Abs delta max:            {report['pairs']['absolute_delta_ms_max']:.3f} ms" if deltas_ms else "Abs delta max:            n/a")
    print("Clock domain verified:   NO — check RealSense timestamp semantics before treating pairs as synchronized.")
    print("Files: rgb_depth_pairs.csv, unmatched_frames.csv, association_report.json")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, csv.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
