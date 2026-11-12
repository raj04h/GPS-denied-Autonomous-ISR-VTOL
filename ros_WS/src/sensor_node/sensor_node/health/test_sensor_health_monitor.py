import json
import time
from collections import deque

import pytest
import rclpy
from sensor_msgs.msg import Image

from sensor_node.health.sensor_health_monitor import SensorHealthMonitor


class FakePublisher:
    def __init__(self):
        self.messages = []

    def publish(self, message):
        self.messages.append(message)


@pytest.fixture(scope="module", autouse=True)
def ros_context():
    already_ok = rclpy.ok()
    if not already_ok:
        rclpy.init()

    yield

    if not already_ok and rclpy.ok():
        rclpy.shutdown()


@pytest.fixture
def monitor():
    node = SensorHealthMonitor()
    node.publisher = FakePublisher()

    yield node

    node.destroy_node()


def set_healthy_stream(stream, now):
    """Prepare deterministic arrival history for a healthy 15/50 Hz stream."""
    period = 1.0 / stream.expected_rate_hz
    stream.arrivals = deque([
        now - 2 * period,
        now - period,
        now,
    ])
    stream.last_arrival = now
    stream.max_arrival_gap_s = 0.0
    stream.estimated_missing_messages = 0
    stream.source_timestamp_regressions = 0
    stream.source_timestamp_valid = True
    stream.total_messages = 3


def read_health(node):
    node.publish_health()
    assert node.publisher.messages
    return json.loads(node.publisher.messages[-1].data)


def test_initial_streams_report_no_data(monitor):
    result = read_health(monitor)

    assert result["overall_status"] == "STALE"
    for name in ("rgb", "depth", "imu"):
        assert result["streams"][name]["status"] == "NO_DATA"


def test_regular_streams_report_healthy(monitor):
    now = time.monotonic()

    for stream in monitor.streams.values():
        set_healthy_stream(stream, now)

    result = read_health(monitor)

    assert result["overall_status"] == "HEALTHY"
    for stream in result["streams"].values():
        assert stream["status"] == "HEALTHY"


def test_stale_stream_is_reported(monitor):
    now = time.monotonic()

    for stream in monitor.streams.values():
        set_healthy_stream(stream, now)

    monitor.streams["rgb"].last_arrival = now - 2.0

    result = read_health(monitor)

    assert result["streams"]["rgb"]["status"] == "STALE"
    assert result["overall_status"] == "STALE"


def test_large_arrival_gap_is_degraded(monitor):
    now = time.monotonic()

    for stream in monitor.streams.values():
        set_healthy_stream(stream, now)

    monitor.streams["rgb"].max_arrival_gap_s = (
        monitor.gap_warning_factor
        / monitor.streams["rgb"].expected_rate_hz
        + 0.01
    )

    result = read_health(monitor)

    assert result["streams"]["rgb"]["status"] == "DEGRADED"
    assert result["overall_status"] == "DEGRADED"


def test_timestamp_regression_is_degraded(monitor):
    now = time.monotonic()

    for stream in monitor.streams.values():
        set_healthy_stream(stream, now)

    stream = monitor.streams["imu"]
    stream.source_timestamp_regressions = 1

    result = read_health(monitor)

    assert result["streams"]["imu"]["status"] == "DEGRADED"
    assert result["overall_status"] == "DEGRADED"


def test_record_detects_source_timestamp_regression(monitor):
    first = Image()
    first.header.stamp.sec = 2
    first.header.stamp.nanosec = 0

    second = Image()
    second.header.stamp.sec = 1
    second.header.stamp.nanosec = 0

    monitor.record("rgb", first)
    monitor.record("rgb", second)

    stream = monitor.streams["rgb"]
    assert stream.source_timestamp_regressions == 1
    assert stream.last_source_stamp_ns == 1_000_000_000


def test_stream_recovers_after_stale_period(monitor):
    now = time.monotonic()

    for stream in monitor.streams.values():
        set_healthy_stream(stream, now)

    rgb = monitor.streams["rgb"]
    rgb.last_arrival = now - 2.0

    stale_result = read_health(monitor)
    assert stale_result["streams"]["rgb"]["status"] == "STALE"

    # Simulate a resumed stream with a fresh, regular arrival history.
    recovered_now = time.monotonic()
    set_healthy_stream(rgb, recovered_now)

    recovered_result = read_health(monitor)
    assert recovered_result["streams"]["rgb"]["status"] == "HEALTHY"
    assert recovered_result["overall_status"] == "HEALTHY"


def test_health_json_contains_required_fields(monitor):
    result = read_health(monitor)

    assert "timestamp_monotonic_s" in result
    assert "overall_status" in result
    assert set(result["streams"]) == {"rgb", "depth", "imu"}

    required = {
        "topic",
        "status",
        "observed_rate_hz",
        "expected_rate_hz",
        "last_message_age_s",
        "total_messages",
        "max_arrival_gap_s",
        "estimated_missing_messages",
        "source_timestamp_valid",
        "source_timestamp_regressions",
    }

    for stream in result["streams"].values():
        assert required.issubset(stream.keys())

