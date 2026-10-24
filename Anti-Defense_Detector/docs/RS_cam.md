# Intel RealSense D455 — Setup and Verification

## Objective
What are we trying to accomplish?

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
How does information move through the system?

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
        └── RGB/Depth TF
```

## Procedure
Exact implementation/setup procedure.

1. Connected the Intel RealSense D455 to the Jetson Orin NX.

2. Verified USB enumeration:

```bash
lsusb
```

The D455 was detected as:

```text
Intel Corp. Intel(R) RealSense(TM) Depth Camera 455
ID 8086:0b5c
```

3. Verified the USB topology:

```bash
lsusb -t
```

The D455 was detected at:

```text
480M
```

indicating USB 2.0 operation with the currently available hardware.

4. Verified Linux video interfaces:

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

5. Verified direct depth frame acquisition using V4L2:

```bash
v4l2-ctl --stream-mmap --stream-count=30
```

Depth frames were successfully acquired.

6. Verified direct RGB frame acquisition using V4L2.

RGB frames were successfully acquired.

7. Installed the ROS Humble RealSense SDK:

```bash
sudo apt install -y ros-humble-librealsense2
```

8. Installed the ROS 2 RealSense camera driver:

```bash
sudo apt install -y \
    ros-humble-realsense2-camera \
    ros-humble-realsense2-description
```

9. Launched the RealSense ROS 2 driver:

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

10. Verified ROS 2 camera topics.

11. Verified RGB topic rate.

12. Verified depth frame contents and depth statistics.

13. Verified camera information topics.

14. Verified RGB/depth TF availability.

15. Investigated the D455 HID/IMU interface using:

```text
/dev/hidraw0
evtest
HID report descriptor inspection
RealSense SDK sensor enumeration
ROS 2 RealSense driver diagnostics
```

## Configuration
Versions, parameters, paths, environment variables, etc.

Platform:

```text
Hardware: NVIDIA Jetson Orin NX 16GB
Architecture: aarch64
OS: Ubuntu 22.04.5 LTS
ROS 2: Humble
```

RealSense:

```text
Device: Intel RealSense D455
VID:PID: 8086:0b5c
Serial: 235422301824
Firmware: 5.17.0.9
librealsense: 2.58.4
```

Current USB connection:

```text
USB 2.0
480M
```

ROS 2 node:

```text
/camera/camera
```

RGB topic:

```text
/camera/camera/color/image_raw
```

Depth topic:

```text
/camera/camera/depth/image_rect_raw
```

RGB CameraInfo:

```text
/camera/camera/color/camera_info
```

Depth CameraInfo:

```text
/camera/camera/depth/camera_info
```

Extrinsics:

```text
/camera/camera/extrinsics/depth_to_color
/camera/camera/extrinsics/depth_to_depth
```

## Validation
Tests performed and expected vs. actual results.

| Test | Expected | Actual | Result |
|---|---|---|---:|
| USB enumeration | D455 detected | `8086:0b5c` detected | PASS |
| Linux video interfaces | `/dev/video*` available | `/dev/video0`–`/dev/video5` | PASS |
| Device identity | D455 identity available | Serial `235422301824`, firmware `5.17.0.9` | PASS |
| SDK detection | One D455 detected | `DEVICE_COUNT=1` | PASS |
| RGB acquisition | RGB frames | Frames successfully captured | PASS |
| Depth acquisition | Depth frames | Frames successfully captured | PASS |
| ROS 2 RGB | Image topic with data | ~14.986 Hz observed | PASS |
| ROS 2 depth | Image topic with data | Valid 640×480 `16UC1` depth data | PASS |
| Depth data quality | Non-zero depth values | 250423/307200 pixels non-zero | PASS |
| CameraInfo | Calibration information | RGB/depth CameraInfo available | PASS |
| RGB/depth TF | Valid transform | Transform became available after startup | PASS |
| USB 3.x | 5000M/10000M-class connection | Current connection 480M | NOT VERIFIED |
| IMU | Motion data available | Motion Module unavailable to SDK/ROS driver | NOT VERIFIED |

The RGB ROS 2 stream was measured at approximately 14.986 Hz.

The depth stream produced actual data, with the tested run showing variable rates of approximately 3.4–5.86 Hz.

The depth data contained 250423 non-zero pixels out of 307200 pixels at 640×480 resolution, with `16UC1` encoding and a measured mean depth of 1692.69 in the captured dataset.

The RGB/depth transform became valid after initial startup messages indicating that the transform was not yet available. The verified transform included approximately `[-0.059, -0.000, 0.000]` translation.

## Result
PASS / FAIL / PARTIAL, with the verified state.

**PARTIAL — D455 perception interface successfully integrated for RGB + depth.**

Verified:

- USB enumeration: PASS.
- Linux interfaces: PASS.
- Device identity: PASS.
- RealSense SDK detection: PASS.
- RGB acquisition: PASS.
- Depth acquisition: PASS.
- ROS 2 RGB interface: PASS.
- ROS 2 depth interface: PASS.
- CameraInfo: PASS.
- RGB/depth TF: PASS.

Not verified:

- USB 3.x operation.
- IMU/motion data.

The D455 is therefore usable as a **ROS 2 RGB + depth perception sensor** with the current hardware configuration.

## Problems & Limitations
Failures encountered and how they were resolved.
What is not yet verified or supported.

1. **USB 3.x was not achieved.**

   The D455 currently enumerates at 480M USB 2.0. The currently available hardware/cable configuration does not provide verified USB 3.x operation.

   This is recorded as a limitation rather than blocking further development.

2. **Depth performance is limited under the current USB 2.0 configuration.**

   RGB operated at approximately 15 Hz in the validated run, while the tested depth stream showed variable lower rates of approximately 3.4–5.86 Hz.

3. **D455 IMU is not currently available.**

   The D455 exposes a HID interface, but raw HID capture produced no motion reports. `evtest` exposed camera/button functionality rather than motion data. The RealSense SDK exposed the Stereo Module and RGB Camera but no Motion Module.

   The ROS 2 driver reported:

```text
No HID info provided, IMU is disabled
HID Motion Sensor Failure
```

   Therefore IMU availability remains unresolved and is not marked as PASS.

4. Initial TF lookup produced a transient invalid-frame/waiting state, after which the RGB/depth transform became available. This was treated as startup behavior rather than a persistent TF failure.

## Summary
Concise final engineering state and significance.

The Intel RealSense D455 is successfully integrated with the Jetson Orin NX and ROS 2 Humble for **RGB + depth perception**.

The complete verified path is:

```text
D455
 ↓
Jetson USB
 ↓
librealsense 2.58.4
 ↓
realsense2_camera
 ↓
ROS 2
 ├── RGB
 ├── Depth
 ├── CameraInfo
 └── RGB/Depth TF
```

This establishes the primary visual/depth sensing interface required for the autonomous UAV perception stack.

The remaining D455 limitations are USB 2.0 operation and unavailable IMU data.

## Next Step
What should be done next?

Return to the **ZeroDrag Strix R0.1 flight controller interface**.

The next objective is to complete:

```text
ZeroDrag Strix
 ↓
USB CDC ACM
 ↓
stable if00 interface
 ↓
MAVROS
 ↓
ROS 2 telemetry
```

Specifically, diagnose why the MAVROS process exited after successfully opening the Strix endpoint and detecting the remote MAVLink address, then verify the resulting ROS 2 telemetry interface.