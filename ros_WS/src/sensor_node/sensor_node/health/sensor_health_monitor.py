
import json
import time
from collections import deque
from dataclasses import dataclass, field

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, Imu
from std_msgs.msg import String


@dataclass
class StreamState:
    """Track arrival timing and source timestamps for one stream."""

    topic: str
    expected_rate_hz: float
    stale_after_s: float
    arrivals: deque = field(default_factory=deque)
    total_messages: int = 0
    last_arrival: float = 0.0
    max_arrival_gap_s: float = 0.0
    estimated_missing_messages: int = 0
    last_source_stamp_ns: int = 0
    source_timestamp_regressions: int = 0
    source_timestamp_valid: bool = False


class SensorHealthMonitor(Node):
    """Publish health summaries for RGB, depth, and IMU streams."""

    def __init__(self):
        super().__init__("sensor_health_monitor")

        self.declare_parameter("window_s", 5.0)
        self.declare_parameter("publish_rate_hz", 1.0)
        self.declare_parameter("expected_camera_rate_hz", 15.0)
        self.declare_parameter("expected_imu_rate_hz", 50.0)
        self.declare_parameter("stale_after_s", 1.0)
        self.declare_parameter("gap_warning_factor", 1.8)

        self.window_s = max(
            1.0, float(self.get_parameter("window_s").value)
        )
        camera_rate = float(
            self.get_parameter("expected_camera_rate_hz").value
        )
        imu_rate = float(
            self.get_parameter("expected_imu_rate_hz").value
        )
        stale_after = float(
            self.get_parameter("stale_after_s").value
        )
        self.gap_warning_factor = max(
            1.0, float(self.get_parameter("gap_warning_factor").value)
        )

        self.streams = {
            "rgb": StreamState(
                "/camera/camera/color/image_raw",
                camera_rate,
                stale_after,
            ),
            "depth": StreamState(
                "/camera/camera/depth/image_rect_raw",
                camera_rate,
                stale_after,
            ),
            "imu": StreamState(
                "/sensor/imu",
                imu_rate,
                stale_after,
            ),
        }

        message_types = {"rgb": Image, "depth": Image, "imu": Imu}

        for name, state in self.streams.items():
            self.create_subscription(
                message_types[name],
                state.topic,
                lambda msg, stream_name=name: self.record(stream_name, msg),
                qos_profile_sensor_data,
            )

        self.publisher = self.create_publisher(
            String, "/sensor_management/health", 10
        )

        publish_rate = max(
            0.1, float(self.get_parameter("publish_rate_hz").value)
        )
        self.timer = self.create_timer(
            1.0 / publish_rate, self.publish_health
        )

        self.get_logger().info(
            "Sensor health monitor v2 started: RGB, depth, and IMU."
        )

    def record(self, name, msg):
        """Record arrival time and inspect the message's source timestamp."""
        now = time.monotonic()
        stream = self.streams[name]

        if stream.last_arrival > 0.0:
            gap = now - stream.last_arrival
            stream.max_arrival_gap_s = max(
                stream.max_arrival_gap_s, gap
            )

            expected_period = 1.0 / stream.expected_rate_hz
            if gap > self.gap_warning_factor * expected_period:
                estimated = max(1, round(gap / expected_period) - 1)
                stream.estimated_missing_messages += estimated

        stamp = msg.header.stamp
        stamp_ns = int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)

        if stamp_ns > 0:
            if (
                stream.last_source_stamp_ns > 0
                and stamp_ns < stream.last_source_stamp_ns
            ):
                stream.source_timestamp_regressions += 1

            stream.last_source_stamp_ns = stamp_ns
            stream.source_timestamp_valid = True
        else:
            stream.source_timestamp_valid = False

        stream.arrivals.append(now)
        stream.last_arrival = now
        stream.total_messages += 1

        while (
            stream.arrivals
            and now - stream.arrivals[0] > self.window_s
        ):
            stream.arrivals.popleft()

    def publish_health(self):
        """Publish stream diagnostics and an aggregate status."""
        now = time.monotonic()
        results = {}

        for name, stream in self.streams.items():
            age = (
                now - stream.last_arrival
                if stream.last_arrival > 0.0
                else None
            )

            times = list(stream.arrivals)
            rate = (
                (len(times) - 1) / (times[-1] - times[0])
                if len(times) >= 2 and times[-1] > times[0]
                else 0.0
            )

            gap_warning = (
                stream.max_arrival_gap_s
                > self.gap_warning_factor / stream.expected_rate_hz
            )

            if age is None:
                status = "NO_DATA"
            elif age > stream.stale_after_s:
                status = "STALE"
            elif rate < 0.8 * stream.expected_rate_hz:
                status = "DEGRADED"
            elif (
                gap_warning
                or stream.source_timestamp_regressions > 0
            ):
                status = "DEGRADED"
            else:
                status = "HEALTHY"

            results[name] = {
                "topic": stream.topic,
                "status": status,
                "observed_rate_hz": round(rate, 2),
                "expected_rate_hz": stream.expected_rate_hz,
                "last_message_age_s": (
                    round(age, 3) if age is not None else None
                ),
                "total_messages": stream.total_messages,
                "max_arrival_gap_s": round(
                    stream.max_arrival_gap_s, 4
                ),
                "estimated_missing_messages": (
                    stream.estimated_missing_messages
                ),
                "source_timestamp_valid": (
                    stream.source_timestamp_valid
                ),
                "source_timestamp_regressions": (
                    stream.source_timestamp_regressions
                ),
            }

        statuses = [item["status"] for item in results.values()]

        if any(status in ("NO_DATA", "STALE") for status in statuses):
            overall = "STALE"
        elif any(status == "DEGRADED" for status in statuses):
            overall = "DEGRADED"
        else:
            overall = "HEALTHY"

        message = String()
        message.data = json.dumps({
            "timestamp_monotonic_s": round(now, 6),
            "overall_status": overall,
            "streams": results,
        })
        self.publisher.publish(message)


def main(args=None):
    rclpy.init(args=args)
    node = SensorHealthMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
