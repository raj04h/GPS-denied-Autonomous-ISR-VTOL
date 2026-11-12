# Intel RealSense D455 — Setup and Verification



## Objective

Establish and validate the Intel RealSense D455 interface with the NVIDIA Jetson Orin NX and ROS 2 Humble for autonomous UAV perception.

The objective is to verify:

- USB enumeration and Linux device interfaces.
- RealSense SDK device detection.
- RGB image acquisition.
- Depth image acquisition.
- ROS 2 RGB and depth interfaces.
- Camera calibration information.
- RGB/depth spatial transform.
- IMU availability.
- Device identity and firmware.
- Current USB performance limitations.

## Dataflow

```text
Intel RealSense D455
        │
        ▼
Jetson USB subsystem
        │
        ├── V4L2 video interfaces
        │
        ├── HID interface
        │
        ▼
librealsense2 2.58.4
        │
        ▼
realsense2_camera ROS 2 driver
        │
        ├── RGB
        │     └── /camera/camera/color/image_raw
        │
        ├── Depth
        │     └── /camera/camera/depth/image_rect_raw
        │
        ├── Camera information
        │     ├── /camera/camera/color/camera_info
        │     └── /camera/camera/depth/camera_info
        │
        └── RGB/Depth extrinsics
              ├── /camera/camera/extrinsics/depth_to_color
              └── /camera/camera/extrinsics/depth_to_depth
```

## Procedure

### 1. Connect the D455

The Intel RealSense D455 was connected directly to the Jetson Orin NX.

### 2. Verify USB enumeration

```bash
lsusb
```

The device was detected as:

```text
Bus 001 Device 004: ID 8086:0b5c Intel Corp. Intel(R) RealSense(TM) Depth Camera 455
```

The verified USB identity is:

```text
VID:PID = 8086:0b5c
```

### 3. Verify USB topology and connection speed

```bash
lsusb -t
```

The D455 was found on the Jetson USB 1 bus at:

```text
480M
```

Therefore the current physical connection is operating as:

```text
USB 2.0
```

USB 3.x operation was not achieved with the currently available hardware/cable configuration.

### 4. Verify Linux video interfaces

```bash
v4l2-ctl --list-devices
```

The D455 exposed:

```text
/dev/video0
/dev/video1
/dev/video2
/dev/video3
/dev/video4
/dev/video5
```

The interfaces were successfully recognized by the Jetson Linux V4L2 subsystem.

### 5. Verify direct depth acquisition

A direct V4L2 capture was performed:

```bash
v4l2-ctl --stream-mmap --stream-count=30
```

Depth frames were successfully acquired.

The captured depth data was confirmed to contain valid depth values.

### 6. Verify direct RGB acquisition

A direct V4L2 capture was performed for the RGB interface.

RGB frames were successfully acquired.

### 7. Install the RealSense SDK

The ROS Humble RealSense SDK package was installed:

```bash
sudo apt install -y ros-humble-librealsense2
```

Installed library version:

```text
librealsense2 2.58.4
```

### 8. Install the ROS 2 RealSense driver

```bash
sudo apt install -y \
    ros-humble-realsense2-camera \
    ros-humble-realsense2-description
```

### 9. Launch the RealSense ROS 2 driver

```bash
source /opt/ros/humble/setup.bash

ros2 launch realsense2_camera rs_launch.py \
    enable_color:=true \
    enable_depth:=true \
    enable_infra1:=false \
    enable_infra2:=false \
    enable_gyro:=true \
    enable_accel:=true
```

The driver successfully detected the D455 and reported:

```text
RealSense ROS v4.58.4
LibRealSense v2.58.4
Device: RealSense D455
Serial: 235422301824
Firmware: 5.17.0.9
USB Type: 2.1
```

The driver reached:

```text
RealSense Node Is Up!
```

The configured RGB and depth streams were:

```text
Depth: 640x480 @ 15 Hz, Z16
Color: 640x480 @ 15 Hz, RGB8
```

### 10. Verify ROS 2 camera topics

```bash
ros2 topic list | grep '^/camera/camera/' | sort
```

Verified topics:

```text
/camera/camera/color/camera_info
/camera/camera/color/image_raw
/camera/camera/color/metadata
/camera/camera/depth/camera_info
/camera/camera/depth/image_rect_raw
/camera/camera/depth/metadata
/camera/camera/extrinsics/depth_to_color
/camera/camera/extrinsics/depth_to_depth
```

### 11. Verify RGB stream rate

```bash
ros2 topic hz /camera/camera/color/image_raw
```
### Visual Feed [RGB + Depth]

```bash
DISPLAY=:10 XAUTHORITY=/home/hraj/.Xauthority \
ros2 run rqt_image_view rqt_image_view
```

The RGB stream initially demonstrated approximately:

```text
14.999 Hz
```

Subsequent measurements under the USB 2.0 configuration showed periods of lower effective throughput and transport stalls, including approximately 10.6–12.5 Hz windows.

The RGB stream remained functional.

### 12. Verify depth stream rate

```bash
ros2 topic hz /camera/camera/depth/image_rect_raw
```

The depth stream initially demonstrated approximately:

```text
14.99 Hz
```

with approximately:

```text
0.066–0.067 s
```

inter-frame timing during the stable measurement window.

Later measurements under USB 2.0 showed lower effective throughput and occasional transport gaps, including approximately 12.1 Hz windows.

The depth stream remained functional.

### 13. Verify depth image contents

The depth topic was verified as:

```text
640 x 480
encoding: 16UC1
```

A captured dataset contained:

```text
Non-zero pixels: 250423 / 307200
Minimum depth: 0
Maximum depth: 14450
Mean depth: 1692.69
```

This confirmed that the depth stream contained actual depth measurements rather than an empty image stream.

### 14. Verify CameraInfo

The following calibration-information topics were verified:

```text
/camera/camera/color/camera_info
/camera/camera/depth/camera_info
```

RealSense SDK enumeration also successfully reported camera intrinsics and depth/color extrinsic information.

### 15. Verify RGB/depth extrinsics

The RealSense driver exposed:

```text
/camera/camera/extrinsics/depth_to_color
/camera/camera/extrinsics/depth_to_depth
```

The verified depth-to-color translation was approximately:

```text
[-0.059, -0.000, 0.000] m
```

with rotation close to identity.

This transform represents the **internal D455 depth-to-color calibration**.

It is not the UAV body-to-camera extrinsic calibration.

### 16. Verify D455 device identity

RealSense SDK enumeration identified:

```text
Name: RealSense D455
Serial: 235422301824
Firmware: 5.17.0.9
Product ID: 0B5C
Product Line: D400
Connection Type: USB
USB Type Descriptor: 2.1
IMU Type: BMI085
Advanced Mode: YES
```

The SDK reported:

```text
DEVICE_COUNT=1
```

and detected:

```text
SENSORS=2
SENSOR=Stereo Module
SENSOR=RGB Camera
```

### 17. Investigate the D455 HID/IMU interface

The D455 exposes a HID interface:

```text
/dev/hidraw0
```

The HID device was verified as belonging to the D455 through its device path and USB identifiers:

```text
VID: 8086
PID: 0B5C
```

A HID report descriptor was successfully read from:

```text
/sys/class/hidraw/hidraw0/device/report_descriptor
```

The Linux kernel successfully bound the HID interface using `hid-generic`.

However, a direct read test from `/dev/hidraw0` produced no motion reports during the observation period.

The RealSense ROS driver reported:

```text
No HID info provided, IMU is disabled
HID Motion Sensor Failure (continuing as partial device): bad optional access
```

The RealSense SDK identified the hardware IMU type as:

```text
BMI085
```

but did not expose usable gyro/accelerometer stream profiles.

No ROS 2 gyro, accelerometer, or combined IMU topics were therefore available.

## Configuration

### Platform

```text
Hardware: NVIDIA Jetson Orin NX 16GB
Architecture: aarch64
OS: Ubuntu 22.04.5 LTS
Jetson Linux: R36.5.2
ROS 2: Humble
```

### RealSense

```text
Device: Intel RealSense D455
VID:PID: 8086:0b5c
Serial: 235422301824
Firmware: 5.17.0.9
Product ID: 0B5C
Product Line: D400
IMU hardware: BMI085
```

### Software

```text
librealsense2: 2.58.4
realsense2_camera: ROS 2 Humble package
RealSense ROS wrapper: 4.58.4
```

### Current USB connection

```text
USB Type: 2.1
Link speed: 480M
Effective mode: USB 2.0
```

### ROS 2 node

```text
/camera/camera
```

### RGB

```text
Topic:
/camera/camera/color/image_raw

Resolution:
640x480

Format:
RGB8

Configured rate:
15 Hz
```

### Depth

```text
Topic:
/camera/camera/depth/image_rect_raw

Resolution:
640x480

Format:
Z16 / 16UC1

Configured rate:
15 Hz
```

### CameraInfo

```text
/camera/camera/color/camera_info
/camera/camera/depth/camera_info
```

### RealSense extrinsics

```text
/camera/camera/extrinsics/depth_to_color
/camera/camera/extrinsics/depth_to_depth
```

### IMU

```text
Hardware IMU: BMI085
ROS 2 gyro topic: not available
ROS 2 accel topic: not available
ROS 2 combined IMU topic: not available
```

## Validation

| Test | Expected | Actual | Result |
|---|---|---|---|
| USB enumeration | D455 detected | `8086:0b5c` detected | PASS |
| Linux video interfaces | `/dev/video*` available | `/dev/video0`–`/dev/video5` | PASS |
| USB topology | Camera connected | 480M USB 2.0 | PASS |
| USB 3.x | 5/10 Gbps-class connection | Current link is 480M | NOT VERIFIED |
| Device identity | D455 identity available | Serial `235422301824`, firmware `5.17.0.9` | PASS |
| SDK detection | One D455 detected | `DEVICE_COUNT=1` | PASS |
| SDK sensor enumeration | Camera sensors detected | Stereo + RGB | PASS |
| RGB acquisition | RGB frames available | Frames successfully captured | PASS |
| Depth acquisition | Depth frames available | Frames successfully captured | PASS |
| ROS 2 RGB | RGB image topic with data | ~15 Hz initially; later transport stalls | PASS |
| ROS 2 depth | Depth image topic with data | ~15 Hz initially; later transport stalls | PASS |
| Depth data | Non-zero depth values | 250423/307200 non-zero in captured dataset | PASS |
| RGB CameraInfo | Calibration data | Available | PASS |
| Depth CameraInfo | Calibration data | Available | PASS |
| Depth → Color extrinsic | Transform available | Available | PASS |
| D455 HID | HID endpoint available | `/dev/hidraw0` | PASS |
| D455 IMU hardware | IMU identified | BMI085 identified | PASS |
| D455 IMU data | Gyro/accel reports available | No usable motion reports | PARTIAL |
| ROS 2 IMU topics | IMU topics available | Not available | NOT VERIFIED |

## Result

**PARTIAL — Intel RealSense D455 successfully integrated for RGB + depth perception, with IMU unavailable under the current connection.**

Verified:

- USB enumeration: **PASS**
- Linux V4L2 interfaces: **PASS**
- Device identity: **PASS**
- Firmware identification: **PASS**
- RealSense SDK detection: **PASS**
- RGB acquisition: **PASS**
- Depth acquisition: **PASS**
- ROS 2 RGB interface: **PASS**
- ROS 2 depth interface: **PASS**
- RGB CameraInfo: **PASS**
- Depth CameraInfo: **PASS**
- Internal RGB/depth extrinsics: **PASS**
- D455 HID enumeration: **PASS**
- D455 IMU hardware identification: **PASS**

Partial / not verified:

- USB 3.x operation: **NOT VERIFIED**
- D455 IMU data stream: **PARTIAL / BLOCKED**

The D455 is therefore currently usable as a:

**ROS 2 RGB + depth perception sensor.**

The D455 IMU is **not currently usable as a ROS 2 sensor input**.

## Problems & Limitations

### 1. USB 3.x operation not achieved

The D455 currently enumerates at:

```text
480M
```

which corresponds to USB 2.0 operation.

The available hardware/cable configuration does not provide a verified USB 3.x connection.

This is recorded as a hardware-interface limitation and does not block the RGB/depth integration.

### 2. USB 2.0 limits sensor transport performance

The D455 was configured for:

```text
RGB:   640x480 @ 15 Hz
Depth: 640x480 @ 15 Hz
```

Both streams were successfully acquired.

However, later `ros2 topic hz` measurements showed reduced effective rates and transport stalls under the USB 2.0 connection.

Therefore the current measured rates should **not** be treated as the final performance capability of the D455.

### 3. D455 IMU is unavailable through the current setup

The D455 hardware reports:

```text
IMU Type: BMI085
```

and exposes a HID endpoint.

The HID endpoint is correctly associated with the D455 and has a valid HID report descriptor.

However:

- no usable motion reports were observed from `/dev/hidraw0`;
- librealsense did not expose gyro/accelerometer stream profiles;
- the ROS 2 driver reported HID motion-sensor failure;
- no D455 gyro/accelerometer/IMU ROS topics were created.

Therefore the IMU is classified as:

**PARTIAL / BLOCKED — hardware identified, data path unavailable.**

The D455 should **not** be treated as an available IMU source in the current sensor-fusion architecture.

The issue should be revisited when a verified USB 3.x physical connection is available.

No conclusion was made that the physical BMI085 IMU is defective.

### 4. Internal D455 transform versus UAV extrinsic calibration

The verified:

```text
depth_to_color
```

transform is the D455's internal depth-camera-to-color-camera calibration.

It does **not** establish:

```text
base_link → D455
```

or any other UAV body-to-camera transform.

The UAV-mounted D455 extrinsic calibration remains a Sensor Management task.

### 5. Startup TF behavior

The RGB/depth transform was not immediately available during initial startup and became valid after the RealSense node initialized.
/uas1/mavros/vision_speed
/uas1/mavros/wheel_odometry
/uas1/mavros/wind
/uas1/mavros_node
/uas1/mavros_router
/uas1/transform_listener_impl_aaaaee395548

This was treated as normal startup behavior because the transform subsequently became available and remained usable.

## Summary

The Intel RealSense D455 is successfully integrated with the Jetson Orin NX and ROS 2 Humble as the primary **RGB + depth perception sensor**.

The verified data path is:

```text
Intel RealSense D455
        ↓
Jetson USB subsystem
        ↓
librealsense2 2.58.4
        ↓
realsense2_camera
        ↓
ROS 2 Humble
        ├── RGB
        ├── Depth
        ├── CameraInfo
        └── D455 internal extrinsics
```

The D455 identity, firmware, camera interfaces, RGB stream, depth stream, calibration information, and internal RGB/depth transform have all been verified.

The current hardware limitation is:

```text
D455
 ├── RGB      → PASS
 ├── Depth    → PASS
 ├── CameraInfo → PASS
 ├── Extrinsics → PASS
 ├── USB 3.x  → NOT VERIFIED
 └── IMU      → PARTIAL / BLOCKED
```

The D455 hardware-interface work is therefore considered **closed for the current available configuration**.

The unavailable D455 IMU does not block progression because the ZeroDrag Strix provides the verified primary IMU stream at approximately 50 Hz.

## Next Step

Move from **Hardware Integration** to **Sensor Management**.

The first Sensor Management task is:

**Timestamp and timing characterization of the ZeroDrag Strix IMU and RealSense D455 RGB/depth streams.**

The next engineering sequence is:

```text
Strix IMU
     │
     ├──────────────┐
     │              │
D455 RGB        D455 Depth
     │              │
     └──────┬───────┘
            ▼
    Timestamp Analysis
            │
            ▼
      Time Synchronization
            │
            ▼
     Sensor Calibration
            │
            ▼
       TF / Transforms
            │
            ▼
      Frame Alignment
            │
            ▼
   Synchronized Sensor Dataset
            │
            ▼
    State Estimation / VIO
```

The D455 IMU will remain documented as **PARTIAL / BLOCKED** and should be re-tested when a verified USB 3.x connection becomes available.


