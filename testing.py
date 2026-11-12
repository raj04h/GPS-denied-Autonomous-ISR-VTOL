
#!/usr/bin/env python3
"""Capture Strix RAW_IMU timestamps and host arrival times."""

import csv
import time
from datetime import datetime
from pathlib import Path

from pymavlink import mavutil


# Strix MAVLink interface on the Jetson
STRIX_PORT = (
    "/dev/serial/by-id/"
    "usb-ArduPilot_Zerodrag_Strix_R0.1_"
    "310032001551343131393036-if00"
)

BAUD_RATE = 115200
TEST_DURATION_S = 60
REQUESTED_RATE_HZ = 50

# Data output directory on the Jetson.
# Verify this path before running the script.
DATA_ROOT = Path.home() / "Autonomous-ISR-VTOL" / "data"


def main():
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    output_dir = (
        DATA_ROOT
        / "sensor_management"
        / "strix"
        / "timing"
        / run_id
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "raw_measurements.csv"

    connection = None

    try:
        print(f"Connecting to Strix: {STRIX_PORT}")

        connection = mavutil.mavlink_connection(
            STRIX_PORT,
            baud=BAUD_RATE,
            autoreconnect=False,
        )

        connection.wait_heartbeat(timeout=10)

        print(
            "Heartbeat received. "
            f"System={connection.target_system}, "
            f"Component={connection.target_component}"
        )

        # Request RAW_IMU at a nominal 50 Hz.
        connection.mav.command_long_send(
            connection.target_system,
            connection.target_component,
            mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
            0,
            mavutil.mavlink.MAVLINK_MSG_ID_RAW_IMU,
            int(1_000_000 / REQUESTED_RATE_HZ),
            0,
            0,
            0,
            0,
            0,
        )

        # Allow the stream to settle.
        time.sleep(2)

        start_ns = time.monotonic_ns()
        deadline_ns = (
            start_ns + TEST_DURATION_S * 1_000_000_000
        )
        sample_count = 0

        with csv_path.open(
            "w", newline="", encoding="utf-8"
        ) as csv_file:
            writer = csv.writer(csv_file)

            writer.writerow([
                "sample_index",
                "sensor_time_usec",
                "host_receive_monotonic_ns",
            ])

            print(
                f"Capturing RAW_IMU for "
                f"{TEST_DURATION_S} seconds..."
            )

            while time.monotonic_ns() < deadline_ns:
                message = connection.recv_match(
                    type="RAW_IMU",
                    blocking=True,
                    timeout=1,
                )

                # Record host arrival time immediately after return.
                host_receive_ns = time.monotonic_ns()

                if message is None:
                    continue

                sample_count += 1

                writer.writerow([
                    sample_count,
                    message.time_usec,
                    host_receive_ns,
                ])

                if sample_count % 250 == 0:
                    csv_file.flush()
                    print(f"Captured {sample_count} samples")

            csv_file.flush()

        elapsed_s = (
            time.monotonic_ns() - start_ns
        ) / 1_000_000_000

        print("\nCapture complete.")
        print(f"Samples captured: {sample_count}")
        print(f"Elapsed time: {elapsed_s:.3f} seconds")
        print(f"CSV output: {csv_path}")

        if sample_count == 0:
            print("WARNING: No RAW_IMU samples received.")
        else:
            print("Raw capture completed.")
            print("Timing analysis is the next development stage.")

    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        raise

    finally:
        if connection is not None:
            connection.close()
            print("MAVLink connection closed.")


if __name__ == "__main__":
    main()


