# ZeroDrag Strix R0.1 — Flight Controller Setup and Verification

> **Document purpose:** Record the verified Jetson Orin NX–ZeroDrag Strix R0.1 hardware interface, MAVLink communication, MAVROS integration, and raw IMU telemetry checks.
>
> **Verification scope:** Hardware and ROS 2 interface only. No arming, actuator, setpoint, or flight testing was performed.

## 1. Objective

Establish and verify the Jetson Orin NX interface to the ZeroDrag Strix R0.1 flight controller over USB, including:

- USB device enumeration.
- Linux serial-interface identification.
- Stable device identification.
- MAVLink communication.
- Flight-controller identity verification.
- MAVROS integration with ROS 2 Humble.
- Flight-controller state and telemetry availability through ROS 2.
- Raw IMU telemetry availability and publication-rate verification.

The objective is to establish the flight-controller hardware interface as a reliable input/output interface for the autonomous UAV software stack.

## 2. System Dataflow

```text
ZeroDrag Strix R0.1
        │
        │ USB
        ▼
Jetson Orin NX
        │
        ├── USB CDC ACM
        │
        ▼
/dev/serial/by-id/usb-ArduPilot_Zerodrag_Strix_R0.1_310032001551343131393036-if00
        │
        │ MAVLink 2
        ▼
MAVROS
        │
        ▼
ROS 2 Humble
        │
        ├── /uas1/mavros/state
        ├── /uas1/mavros/imu/data_raw
        ├── /uas1/mavros/imu/mag
        ├── /uas1/mavros/battery
        ├── /uas1/mavros/estimator_status
        └── Other flight-controller telemetry interfaces
```

The preferred flight-controller interface is the first CDC ACM interface:

```text
/dev/ttyACM0
```

Its persistent device path is:

```text
/dev/serial/by-id/usb-ArduPilot_Zerodrag_Strix_R0.1_310032001551343131393036-if00
```

## 3. Hardware and Software Configuration

### 3.1 Flight controller

| Parameter | Verified value |
|---|---|
| Flight controller | ZeroDrag Strix R0.1 |
| Firmware | ArduCopter V4.6.1 |
| Connection | USB |
| USB vendor ID | `1209` |
| USB product ID | `5740` |
| USB driver | `cdc_acm` |

### 3.2 Jetson

| Parameter | Verified value |
|---|---|
| Platform | NVIDIA Jetson Orin NX 16GB |
| OS | Ubuntu 22.04.5 LTS |
| Architecture | `aarch64` |
| Jetson Linux | R36.5.2 |

### 3.3 ROS 2 and MAVLink

| Parameter | Value |
|---|---|
| ROS 2 | Humble |
| MAVROS | `ros-humble-mavros` |
| MAVROS extras | `ros-humble-mavros-extras` |
| MAVROS messages | `ros-humble-mavros-msgs` |
| MAVLink protocol | MAVLink 2 |
| Target system | `1` |
| Target component configured in MAVROS | `1` |
| Serial baud configured for MAVROS test | `115200` |
| ROS namespace | `/uas1` |

### 3.4 Preferred serial device

```text
/dev/serial/by-id/usb-ArduPilot_Zerodrag_Strix_R0.1_310032001551343131393036-if00
```

Resolves to `/dev/ttyACM0` in the recorded test. The device path is preferred over relying directly on `/dev/ttyACM0`, because the persistent path identifies the USB device.

## 4. Setup and Verification Procedure

### 4.1 Verify USB enumeration

Check that Linux detects the Strix:

```bash
lsusb
```

Recorded device:

```text
Bus 001 Device 005: ID 1209:5740 Generic Zerodrag_Strix_R0.1
```

### 4.2 Verify Linux serial interfaces

```bash
ls -l /dev/ttyACM*
```

The Strix exposed:

```text
/dev/ttyACM0
/dev/ttyACM1
```

### 4.3 Verify persistent device identification

```bash
ls -l /dev/serial/by-id/
```

Recorded interfaces:

```text
/dev/serial/by-id/usb-ArduPilot_Zerodrag_Strix_R0.1_310032001551343131393036-if00 -> ../../ttyACM0
/dev/serial/by-id/usb-ArduPilot_Zerodrag_Strix_R0.1_310032001551343131393036-if02 -> ../../ttyACM1
```

The `if00` interface was selected as the preferred MAVLink interface for the recorded tests. The exact physical or firmware role mapping of both CDC interfaces was not independently established.

### 4.4 Verify USB device metadata

Recorded device metadata:

```text
ID_VENDOR=ArduPilot
ID_VENDOR_ID=1209
ID_MODEL=Zerodrag_Strix_R0.1
ID_MODEL_ID=5740
ID_SERIAL=ArduPilot_Zerodrag_Strix_R0.1_310032001551343131393036
```

Both interfaces use the `cdc_acm` driver.

### 4.5 Verify direct MAVLink communication

The preferred interface was opened using `pymavlink`:

```text
/dev/serial/by-id/usb-ArduPilot_Zerodrag_Strix_R0.1_310032001551343131393036-if00
```

A valid MAVLink `HEARTBEAT` was received. The recorded heartbeat information was:

| Field | Observed value |
|---|---|
| System ID | `1` |
| Component ID | `0` |
| Autopilot | ArduPilot |
| Vehicle type | Quadrotor |
| MAVLink version field | `3` |

MAVROS subsequently identified the flight controller as:

```text
ArduCopter V4.6.1
Hardware: Zerodrag_Strix_R0.1
```

> **Configuration note:** The direct heartbeat observation reported component `0`, while the successful MAVROS command below was configured with target component `1`. These are recorded observations; do not silently treat them as the same value. Confirm target-component requirements against the live system if this configuration is revisited.

### 4.6 Install and verify MAVROS

MAVROS and its ROS 2 dependencies were installed using:

```bash
sudo apt install -y ros-humble-mavros ros-humble-mavros-extras ros-humble-mavros-msgs
```

Verify the package prefix:

```bash
ros2 pkg prefix mavros
```

Recorded result:

```text
/opt/ros/humble
```

### 4.7 Start MAVROS using the persistent FC path

Source ROS 2:

```bash
source /opt/ros/humble/setup.bash
```

Start MAVROS:

```bash
ros2 run mavros mavros_node \
  --ros-args \
  -r __ns:=/uas1 \
  -p fcu_url:=/dev/serial/by-id/usb-ArduPilot_Zerodrag_Strix_R0.1_310032001551343131393036-if00:115200 \
  -p fcu_protocol:=v2.0 \
  -p tgt_system:=1 \
  -p tgt_component:=1
```

The direct `mavros_node` configuration was used because the initial `apm.launch` test experienced connection/request timeouts and subsequently exited.

> **Serial-port ownership:** MAVROS and a direct `pymavlink` test must not access the same flight-controller serial interface simultaneously. Stop one client cleanly before starting the other.

A custom publisher command also appeared in the original setup notes:

```bash
ros2 run sensor_node strix_imu_publisher
```

Its presence in the notes does not establish that it is required or that it was part of the verified MAVROS data path. Do not start it alongside MAVROS if it opens the same FC serial port. First inspect its implementation and serial-port ownership.

### 4.8 Verify MAVROS connection and FC state

List ROS 2 nodes:

```bash
ros2 node list
```

Recorded MAVROS-related nodes:

```text
/uas1/mavros
/uas1/mavros_node
/uas1/mavros_router
```

Inspect the flight-controller state:

```bash
ros2 topic echo /uas1/mavros/state --once
```

Recorded state:

```yaml
connected: true
armed: false
guided: false
manual_input: true
mode: STABILIZE
system_status: 3
```

### 4.9 Verify FC ROS 2 telemetry interfaces

List MAVROS topics:

```bash
ros2 topic list | grep '/uas1/mavros/' | sort
```

Recorded interfaces included:

```text
/uas1/mavros/battery
/uas1/mavros/estimator_status
/uas1/mavros/extended_state
/uas1/mavros/global_position/...
/uas1/mavros/imu/data
/uas1/mavros/imu/data_raw
/uas1/mavros/imu/mag
/uas1/mavros/local_position/...
/uas1/mavros/state
/uas1/mavros/statustext/recv
/uas1/mavros/sys_status
/uas1/mavros/time_reference
/uas1/mavros/timesync_status
/uas1/mavros/vfr_hud
/uas1/mavros/vibration/raw/vibration
```

The appearance of a topic in the topic list establishes that the interface exists; it does not by itself prove that messages are being published.

### 4.10 Enable raw IMU telemetry

The flight controller initially did not provide the required raw IMU message stream. The legacy stream-rate parameters were observed as zero.

A direct MAVLink `MAV_CMD_SET_MESSAGE_INTERVAL` request was issued for:

| Parameter | Value |
|---|---|
| Message | `RAW_IMU` |
| Message ID | `27` |
| Requested interval | `20000` microseconds |
| Target rate | `50 Hz` |

The request successfully enabled the `RAW_IMU` stream in the recorded test.

### 4.11 Verify raw IMU ROS 2 output

Inspect one message:

```bash
ros2 topic echo /uas1/mavros/imu/data_raw --once
```

Valid `sensor_msgs/msg/Imu` data was received, including angular velocity, linear acceleration, covariance data, and the `base_link` frame.

Measure the publication rate:

```bash
ros2 topic hz /uas1/mavros/imu/data_raw
```

Recorded sustained rate was approximately `49.9 Hz`, with final measurements including:

```text
49.919 Hz
49.940 Hz
```

The original test described the timing jitter as low. No numerical jitter distribution was included in the recorded evidence.

### 4.12 Verify direct FC telemetry independently

With MAVROS stopped, a separate 60-second `pymavlink` test was performed on the preferred interface.

Recorded result:

```text
HEARTBEAT OK
Elapsed: 60.0s
Messages: 3071
Heartbeats: 59
Rate: 51.18 msg/s
```

This independently verified sustained FC-side MAVLink communication during that test.

## 5. Validation Results

| Validation item | Expected | Recorded result | Status |
|---|---|---|---|
| USB enumeration | Strix detected | USB ID `1209:5740` detected | PASS |
| Linux serial interface | ACM interface available | `/dev/ttyACM0`, `/dev/ttyACM1` | PASS |
| Stable identification | Persistent by-id path | Verified | PASS |
| CDC driver | `cdc_acm` | Verified | PASS |
| Direct MAVLink | Heartbeat received | Verified | PASS |
| FC identity | ArduPilot / ArduCopter | ArduCopter V4.6.1 | PASS |
| Hardware identity | ZeroDrag Strix R0.1 | Verified | PASS |
| MAVROS installation | ROS 2 package available | Verified | PASS |
| MAVROS connection | `connected: true` | Verified | PASS |
| FC ROS 2 state | `/uas1/mavros/state` available | Verified | PASS |
| FC telemetry interfaces | MAVROS topics available | Topic interfaces listed | PASS — topic existence only |
| Raw IMU | ROS 2 IMU messages | Verified | PASS |
| Raw IMU rate | Approximately 50 Hz | Approximately 49.9 Hz | PASS |
| Direct MAVLink stability | Continuous heartbeat | 59 heartbeats over 60 s | PASS |

## 6. Result

**PASS — The ZeroDrag Strix R0.1 flight-controller hardware interface was verified at the USB, MAVLink, and MAVROS/ROS 2 interface levels.**

The recorded tests established that the Jetson Orin NX can:

1. Detect the ZeroDrag Strix R0.1 over USB.
2. Identify the FC using stable USB metadata.
3. Access the preferred persistent serial interface.
4. Establish MAVLink communication.
5. Identify the FC as ArduCopter V4.6.1 / `Zerodrag_Strix_R0.1`.
6. Connect the FC to MAVROS.
7. Receive FC state through ROS 2.
8. Acquire raw IMU data through MAVROS.
9. Receive raw IMU telemetry at approximately 50 Hz in the recorded test.

Verified data path:

```text
ZeroDrag Strix R0.1
        ↓
   USB / CDC ACM
        ↓
    Jetson Linux
        ↓
      MAVLink
        ↓
      MAVROS
        ↓
    ROS 2 /uas1
        ↓
FC state + telemetry + raw IMU
```

## 7. Problems, Limitations, and Open Items

### 7.1 Two CDC ACM interfaces

The Strix exposes two interfaces:

```text
if00 → /dev/ttyACM0
if02 → /dev/ttyACM1
```

Both were reported to provide functional MAVLink communication. `if00` was cleaner during testing and is the preferred interface. The exact physical/firmware role mapping of the interfaces was not independently established.

### 7.2 MAVROS launch behavior

The initial `apm.launch` test experienced:

- `AUTOPILOT_VERSION` request timeout.
- Subsequent MAVLink request timeouts.
- Process exit after the initial connection period.

The direct `mavros_node` configuration was subsequently used successfully and remained active until manually stopped.

### 7.3 MAVLink heartbeat interruptions

During MAVROS testing, intermittent messages were observed:

```text
Lost connection, HEARTBEAT timed out
Got HEARTBEAT, connected
```

A separate 60-second direct MAVLink test subsequently maintained continuous heartbeat reception. This supports the conclusion that the FC USB/MAVLink interface was functional during that separate test; it does not erase the earlier MAVROS interruptions or prove uninterrupted operation under all conditions.

### 7.4 FC pre-arm messages

The FC reported messages including:

```text
RC not found
Compass not healthy
Battery 1 low voltage failsafe
```

These were treated as vehicle/pre-arm-state messages, not as evidence of failure of the Jetson–FC USB/MAVLink interface.

No flight, arming, actuator, or setpoint operation was performed during this hardware-interface validation.

### 7.5 Raw IMU versus processed IMU

The verified raw IMU path is:

```text
FC IMU
   ↓
MAVLink RAW_IMU
   ↓
MAVROS
   ↓
/uas1/mavros/imu/data_raw
```

The processed `/uas1/mavros/imu/data` topic was not established as the primary validated IMU source during this phase. The raw IMU stream is the verified source for subsequent sensor-management and state-estimation investigation.

### 7.6 Historical USB controller messages

Earlier testing produced Jetson USB controller messages involving `tegra-xusb` transfer-event errors during previous USB reconnect conditions.

The final sustained direct MAVLink test did not demonstrate an active failure of the Strix interface. These historical observations should be revisited if USB disconnect/reconnect problems recur.

### 7.7 What this verification does not establish

This verification does **not** establish:

- Correct IMU physical units or axis conventions end-to-end.
- Timestamp provenance, clock domain, timestamp accuracy, or camera–IMU synchronization.
- IMU bias/noise characterization or estimator suitability.
- Validity of the processed IMU orientation estimate.
- Camera calibration or camera–IMU extrinsic calibration.
- Localization accuracy, VIO/SLAM performance, navigation accuracy, or flight readiness.
- Persistence of the requested RAW_IMU message interval across a full reboot.

These require separate tests and evidence.

## 8. Full-System Restart: Repeatable IMU Verification Procedure

Use this procedure after restarting the Jetson or flight controller. Keep the flight controller disarmed. **The direct `pymavlink` test and MAVROS must not use the same serial port simultaneously.**

### 8.1 Source ROS 2 and verify the persistent USB path

Run in Terminal 1:

```bash
source /opt/ros/humble/setup.bash
ls -l /dev/serial/by-id/
```

Confirm that the preferred `if00` device exists:

```text
/dev/serial/by-id/usb-ArduPilot_Zerodrag_Strix_R0.1_310032001551343131393036-if00
```

### 8.2 Check whether the FCU port is already in use

```bash
sudo fuser -v /dev/ttyACM0
```

If a process is listed, identify it and stop it cleanly before proceeding. Do not start the direct test while MAVROS or another serial client owns the port.

### 8.3 Run the direct MAVLink/RAW_IMU test

```bash
python3 ~/strix_imu_test.py
```

Previously recorded output was approximately:

```text
Connecting to Strix...
Heartbeat OK: system=1, component=0
RAW_IMU messages in 5 seconds: 250
Approximate rate: 50.0 Hz
```

The script requests MAVLink `RAW_IMU` message ID 27 at a 20,000-microsecond interval (50 Hz), then counts received messages for five seconds. The original notes state that it does not inspect `COMMAND_ACK`.

Wait for the script to exit and close its serial connection before starting MAVROS.

### 8.4 Start MAVROS

Run in Terminal 1 and leave this terminal open:

```bash
source /opt/ros/humble/setup.bash

ros2 run mavros mavros_node \
  --ros-args \
  -r __ns:=/uas1 \
  -p fcu_url:=/dev/serial/by-id/usb-ArduPilot_Zerodrag_Strix_R0.1_310032001551343131393036-if00:115200 \
  -p fcu_protocol:=v2.0 \
  -p tgt_system:=1 \
  -p tgt_component:=1
```

### 8.5 Verify MAVROS state

Open Terminal 2:

```bash
source /opt/ros/humble/setup.bash
ros2 topic echo /uas1/mavros/state --once
```

Check that `connected: true` is reported. The FCU should remain disarmed (`armed: false`) during these diagnostics.

### 8.6 Verify raw IMU rate

In Terminal 2:

```bash
ros2 topic hz /uas1/mavros/imu/data_raw
```

Let it run for 5–10 seconds, then stop with `Ctrl+C`. The previously recorded rate was approximately 49.9–50.0 Hz.

### 8.7 Inspect one raw IMU message

```bash
ros2 topic echo /uas1/mavros/imu/data_raw --once
```

Inspect the timestamp, `frame_id`, `linear_acceleration`, `angular_velocity`, and covariance fields. This inspection is not, by itself, a full units or frame-convention validation.

### 8.8 Optional follow-up checks

```bash
ros2 topic echo /uas1/mavros/imu/data --once
ros2 topic echo /uas1/mavros/imu/mag --once
```

Previous observations:

- `/uas1/mavros/imu/data` did not return an observed message.
- `/uas1/mavros/imu/mag` published zero magnetic-field components with covariance element zero set to `-1.0` (measurement unavailable).

These are separate issues and must not be marked as resolved solely because `data_raw` works.

### 8.9 Verification record

Complete this table after each restart. Do not copy previous results into the actual-result column without rerunning the check.

| Check | Expected / previously observed | Actual result | Status / notes |
|---|---|---|---|
| Stable `if00` serial path exists | Device listed under `/dev/serial/by-id/` | _Record after test_ | Pending |
| Serial port free before direct test | No competing process | _Record after test_ | Pending |
| Direct MAVLink heartbeat | Heartbeat received; system 1, component 0 observed | _Record after test_ | Pending |
| Direct `RAW_IMU` | Approximately 50 Hz after interval request | _Record after test_ | Pending |
| MAVROS state | `connected: true` | _Record after test_ | Pending |
| ROS 2 `/imu/data_raw` | Approximately 50 Hz | _Record after test_ | Pending |
| ROS 2 `/imu/data` | Not yet verified; previously silent | _Record after test_ | Pending |
| ROS 2 `/imu/mag` validity | Previously zero values; unavailable covariance | _Record after test_ | Pending |

**Interpretation:** A successful direct test verifies the FCU-side MAVLink stream after the script requests it. A successful ROS 2 rate test verifies that MAVROS forwards the stream. Recheck after a full reboot to determine whether the requested message interval persists; persistence has not yet been established.

## 9. Conclusion and Next Engineering Phase

The recorded evidence supports closing the **basic hardware-interface integration check** for the ZeroDrag Strix R0.1 at the USB, MAVLink, and MAVROS/ROS 2 interface levels. The raw IMU stream was observed at approximately 50 Hz.

The next phase is **Sensor Management**. The first timing task is to characterize the Strix IMU and RealSense D455 RGB/depth streams. The intended dependency sequence is:

```text
Timestamp and timing characterization
              ↓
       Timestamp validation
              ↓
       Sensor calibration
              ↓
     TF / transform definition
              ↓
         Frame alignment
              ↓
   Synchronized sensor dataset
              ↓
        VIO / state estimation
```

The interface-level PASS must not be interpreted as proof of sensor synchronization, estimator accuracy, autonomous navigation performance, or flight readiness.