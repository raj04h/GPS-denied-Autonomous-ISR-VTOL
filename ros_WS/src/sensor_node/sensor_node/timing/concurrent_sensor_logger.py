#!/usr/bin/env python3

# 1. Imports
import csv
import json
import threading
import time
from datetime import datetime
from pathlib import Path

import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from pymavlink import mavutil


# 2. Configuration
IMU_DEVICE = (
    "/dev/serial/by-id/"
    "usb-ArduPilot_Zerodrag_Strix_R0.1_310032001551343131393036-if00"
)
IMU_BAUD = 115200
IMU_RATE_HZ = 50
RGB_TOPIC = "/camera/camera/color/image_raw"
DEPTH_TOPIC = "/camera/camera/depth/image_rect_raw"
CAPTURE_DURATION_S = 60
OUTPUT_ROOT = Path.home() / "concurrent_sensor_captures"


# 3. Core Logic
class ConcurrentSensorLogger(Node):
    def __init__(self):
        super().__init__("concurrent_sensor_logger")
        self.stop_event = threading.Event()
        self.capture_start_ns = time.monotonic_ns()
        self.capture_start_wall = datetime.now().astimezone().isoformat()
        self.session_dir = OUTPUT_ROOT / datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir.mkdir(parents=True, exist_ok=False)

        self.rgb_file = (self.session_dir / "rgb_timing.csv").open("w", newline="", buffering=1)
        self.depth_file = (self.session_dir / "depth_timing.csv").open("w", newline="", buffering=1)
        self.imu_file = (self.session_dir / "imu.csv").open("w", newline="", buffering=1)
        self.rgb_writer = csv.writer(self.rgb_file)
        self.depth_writer = csv.writer(self.depth_file)
        self.imu_writer = csv.writer(self.imu_file)

        self.rgb_writer.writerow([
            "sample_index", "host_callback_monotonic_ns", "header_stamp_ns",
            "header_frame_id", "height", "width", "encoding"
        ])
        self.depth_writer.writerow([
            "sample_index", "host_callback_monotonic_ns", "header_stamp_ns",
            "header_frame_id", "height", "width", "encoding"
        ])
        self.imu_writer.writerow([
            "sample_index", "host_receive_monotonic_ns", "sensor_time_usec",
            "xacc", "yacc", "zacc", "xgyro", "ygyro", "zgyro",
            "xmag", "ymag", "zmag", "temperature"
        ])

        self.rgb_count = 0
        self.depth_count = 0
        self.imu_count = 0
        self.imu_error = None
        self.mav = None
        self.callback_group = ReentrantCallbackGroup()

        self.create_subscription(
            Image, RGB_TOPIC, self.rgb_callback, qos_profile_sensor_data,
            callback_group=self.callback_group
        )
        self.create_subscription(
            Image, DEPTH_TOPIC, self.depth_callback, qos_profile_sensor_data,
            callback_group=self.callback_group
        )

        self.imu_thread = threading.Thread(
            target=self.imu_reader, name="strix-imu-reader", daemon=True
        )
        self.imu_thread.start()
        self.get_logger().info(f"Capture started: {self.session_dir}")
        self.get_logger().info(f"Duration: {CAPTURE_DURATION_S}s; IMU: {IMU_DEVICE}")
        self.get_logger().info("Waiting for MAVLink heartbeat and requesting RAW_IMU at 50 Hz.")
        self.get_logger().info("Press Ctrl+C to stop early.")

    @staticmethod
    def header_stamp_ns(msg):
        return int(msg.header.stamp.sec) * 1_000_000_000 + int(msg.header.stamp.nanosec)

    def rgb_callback(self, msg):
        host_ns = time.monotonic_ns()
        self.rgb_count += 1
        self.rgb_writer.writerow([
            self.rgb_count, host_ns, self.header_stamp_ns(msg), msg.header.frame_id,
            msg.height, msg.width, msg.encoding
        ])

    def depth_callback(self, msg):
        host_ns = time.monotonic_ns()
        self.depth_count += 1
        self.depth_writer.writerow([
            self.depth_count, host_ns, self.header_stamp_ns(msg), msg.header.frame_id,
            msg.height, msg.width, msg.encoding
        ])

    def imu_reader(self):
        try:
            self.mav = mavutil.mavlink_connection(
                IMU_DEVICE, baud=IMU_BAUD, autoreconnect=True, source_system=255
            )

            heartbeat = self.mav.wait_heartbeat(timeout=10)
            if heartbeat is None:
                raise TimeoutError(
                    "No MAVLink heartbeat received within 10 seconds. "
                    "Check whether another application owns the serial port and "
                    "whether this interface carries MAVLink telemetry."
                )

            target_system = self.mav.target_system
            target_component = self.mav.target_component
            self.get_logger().info(
                f"MAVLink heartbeat received (system={target_system}, "
                f"component={target_component})."
            )

            # Request RAW_IMU at 50 Hz (20,000 microseconds per message).
            self.mav.mav.command_long_send(
                target_system,
                target_component,
                mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
                0,
                mavutil.mavlink.MAVLINK_MSG_ID_RAW_IMU,
                1_000_000 / IMU_RATE_HZ,
                0, 0, 0, 0, 0
            )

            # Compatibility fallback for autopilots/bridges that do not honor
            # SET_MESSAGE_INTERVAL for this message.
            request_sent_ns = time.monotonic_ns()
            fallback_requested = False

            while not self.stop_event.is_set():
                msg = self.mav.recv_match(type="RAW_IMU", blocking=True, timeout=0.5)
                host_ns = time.monotonic_ns()

                if msg is None:
                    if (
                        not fallback_requested
                        and self.imu_count == 0
                        and (host_ns - request_sent_ns) >= 3_000_000_000
                    ):
                        self.mav.mav.request_data_stream_send(
                            target_system,
                            target_component,
                            mavutil.mavlink.MAV_DATA_STREAM_RAW_SENSORS,
                            IMU_RATE_HZ,
                            1
                        )
                        fallback_requested = True
                        self.get_logger().warning(
                            "No RAW_IMU yet; requested RAW_SENSORS stream as fallback."
                        )
                    continue

                self.imu_count += 1
                self.imu_writer.writerow([
                    self.imu_count, host_ns, getattr(msg, "time_usec", ""),
                    getattr(msg, "xacc", ""), getattr(msg, "yacc", ""),
                    getattr(msg, "zacc", ""), getattr(msg, "xgyro", ""),
                    getattr(msg, "ygyro", ""), getattr(msg, "zgyro", ""),
                    getattr(msg, "xmag", ""), getattr(msg, "ymag", ""),
                    getattr(msg, "zmag", ""), getattr(msg, "temperature", "")
                ])

        except Exception as exc:
            self.imu_error = repr(exc)
            self.get_logger().error(f"IMU reader failed: {self.imu_error}")
        finally:
            if self.mav is not None:
                try:
                    self.mav.close()
                except Exception:
                    pass

    def close_files(self):
        self.stop_event.set()
        if hasattr(self, "imu_thread") and self.imu_thread.is_alive():
            self.imu_thread.join(timeout=3.0)

        for f in (self.rgb_file, self.depth_file, self.imu_file):
            try:
                f.flush()
                f.close()
            except Exception:
                pass

        end_ns = time.monotonic_ns()
        metadata = {
            "capture_start_wall_time": self.capture_start_wall,
            "capture_duration_requested_s": CAPTURE_DURATION_S,
            "capture_start_monotonic_ns": self.capture_start_ns,
            "capture_end_monotonic_ns": end_ns,
            "capture_elapsed_s": round((end_ns - self.capture_start_ns) / 1e9, 6),
            "host_clock": "time.monotonic_ns",
            "camera_timestamp_note": (
                "ROS header timestamps are preserved as reported; clock domain and "
                "exposure semantics are not assumed."
            ),
            "host_timestamp_note": (
                "Camera timestamps are taken at ROS callback entry; IMU timestamps "
                "are taken after RAW_IMU is returned by pymavlink."
            ),
            "rgb_topic": RGB_TOPIC,
            "depth_topic": DEPTH_TOPIC,
            "imu_device": IMU_DEVICE,
            "imu_baud": IMU_BAUD,
            "requested_raw_imu_rate_hz": IMU_RATE_HZ,
            "rgb_samples": self.rgb_count,
            "depth_samples": self.depth_count,
            "imu_raw_imu_samples": self.imu_count,
            "imu_error": self.imu_error,
            "synchronization_claim": (
                "Concurrent arrival-time logging only; this does not prove hardware "
                "exposure synchronization or clock offset/drift."
            )
        }
        (self.session_dir / "session_metadata.json").write_text(json.dumps(metadata, indent=2))
        print("\nCapture finished.")
        print(f"Output: {self.session_dir}")
        print(f"RGB samples:      {self.rgb_count}")
        print(f"Depth samples:    {self.depth_count}")
        print(f"RAW_IMU samples:  {self.imu_count}")
        if self.imu_error:
            print(f"IMU reader error: {self.imu_error}")


# 4. Execution
def main():
    rclpy.init()
    node = None
    executor = None
    try:
        node = ConcurrentSensorLogger()
        executor = MultiThreadedExecutor(num_threads=3)
        executor.add_node(node)

        deadline = time.monotonic() + CAPTURE_DURATION_S
        while rclpy.ok() and not node.stop_event.is_set() and time.monotonic() < deadline:
            executor.spin_once(timeout_sec=0.1)

    except KeyboardInterrupt:
        print("\nStop requested by user.")
    finally:
        if executor is not None:
            executor.shutdown(timeout_sec=2.0)
        if node is not None:
            node.close_files()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()