"""Publish Strix RAW_IMU data as a ROS 2 Imu message."""

from pymavlink import mavutil
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu


class StrixImuPublisher(Node):
    def __init__(self):
        super().__init__("strix_imu_publisher")

        self.declare_parameter(
            "port",
            "/dev/serial/by-id/usb-ArduPilot_Zerodrag_Strix_R0.1_310032001551343131393036-if00",
        )
        self.declare_parameter("baud", 115200)
        self.declare_parameter("frame_id", "strix_imu_link")

        port = str(self.get_parameter("port").value)
        baud = int(self.get_parameter("baud").value)
        self.frame_id = str(self.get_parameter("frame_id").value)

        self.publisher = self.create_publisher(
            Imu, "/sensor/imu", 10
        )

        self.connection = mavutil.mavlink_connection(
            port, baud=baud, autoreconnect=True
        )

        self.get_logger().info("Waiting for MAVLink heartbeat...")
        heartbeat = self.connection.wait_heartbeat(timeout=10)

        if heartbeat is None:
            self.connection.close()
            raise RuntimeError(
                "No heartbeat received. Check the port, baud rate, "
                "and whether another process owns the serial port."
            )

        self.get_logger().info(
            f"MAVLink connected: system={self.connection.target_system}, "
            f"component={self.connection.target_component}"
        )

        self.timer = self.create_timer(0.005, self.read_mavlink)

    def read_mavlink(self):
        for _ in range(100):
            msg = self.connection.recv_match(blocking=False)

            if msg is None:
                break

            if msg.get_type() != "RAW_IMU":
                continue

            imu = Imu()
            imu.header.stamp = self.get_clock().now().to_msg()
            
            imu.header.frame_id = self.frame_id

            # Standard MAVLink RAW_IMU units:
            # acceleration: milligravity; gyro: milliradians/second.
            imu.orientation_covariance[0] = -1.0

            imu.linear_acceleration.x = float(msg.xacc) * 9.80665 / 1000.0
            imu.linear_acceleration.y = float(msg.yacc) * 9.80665 / 1000.0
            imu.linear_acceleration.z = float(msg.zacc) * 9.80665 / 1000.0

            imu.angular_velocity.x = float(msg.xgyro) / 1000.0
            imu.angular_velocity.y = float(msg.ygyro) / 1000.0
            imu.angular_velocity.z = float(msg.zgyro) / 1000.0

            self.publisher.publish(imu)


def main(args=None):
    rclpy.init(args=args)
    node = None

    try:
        node = StrixImuPublisher()
        rclpy.spin(node)
    except (KeyboardInterrupt, RuntimeError) as exc:
        if str(exc):
            print(f"Strix IMU publisher stopped: {exc}")
    finally:
        if node is not None:
            node.connection.close()
            node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()