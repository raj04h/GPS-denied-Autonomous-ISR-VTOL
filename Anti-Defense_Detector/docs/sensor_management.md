# SM-B4.3 — Clock-Domain Relationship

**Project:** Civilian ISR UAV — disaster response, forest, mining and tunnel search operations  
**Dataset:** `20261026_212010`  
**Assessment date:** 18 November 2026  
**Status:** Evidence review completed with limitations

## 1. Purpose

Document the available evidence concerning the relationship between the D455 RGB/depth timestamps, Strix `RAW_IMU.time_usec`, and Jetson host monotonic timestamps. This record distinguishes observed timestamp behaviour from verified clock offset, clock drift, and physical measurement-time alignment.

## 2. Work-package status

| ID | Assessment | Status |
|---|---|---|
| B4.3.1 | Review B4.2 findings | Complete |
| B4.3.2 | Identify comparable timestamp records | Complete |
| B4.3.3 | Review clock-origin differences | Complete with limitations |
| B4.3.4 | Assess available offset evidence | Closed with limitations |
| B4.3.5 | Assess available drift evidence | Closed as evidence assessment; true drift not established |
| B4.3.6 | Document uncertainty and limitations | Complete |

## 3. Timestamp evidence

| Stream | Recorded timestamp | Host timestamp | Evidence interpretation |
|---|---|---|---|
| D455 RGB | ROS `header_stamp_ns` | `host_callback_monotonic_ns` | Camera-reported timestamp paired with host callback-entry time |
| D455 depth | ROS `header_stamp_ns` | `host_callback_monotonic_ns` | Camera-reported timestamp paired with host callback-entry time |
| Strix IMU | MAVLink `RAW_IMU.time_usec` (`sensor_time_usec`) | `host_receive_monotonic_ns` | Strix-reported timestamp paired with host time recorded after `recv_match()` returns |

The host timestamp basis is `time.monotonic_ns()`. Camera host timestamps are sampled at ROS callback entry. The IMU host timestamp is sampled after the MAVLink message is returned by `pymavlink`.

The active D455 timestamp domain and exposure-time semantics remain unverified. The Strix timestamp is defined by the MAVLink message schema as a microsecond timestamp that may represent UNIX epoch time or time since system boot. The observed magnitude is consistent with a boot-relative timestamp, but the actual Strix firmware clock origin and measurement-time semantics have not been confirmed.

## 4. Dataset and timestamp-order findings

Dataset directory:

`~/Autonomous-ISR-VTOL/data/concurrent_sensor_captures/20261026_212010/`

| Stream | Samples | Sensor elapsed | Host elapsed | Sensor timestamps strictly increasing | Host timestamps strictly increasing |
|---|---:|---:|---:|---|---|
| RGB | 836 | 60.048716 s | 60.048705 s | Yes | Yes |
| Depth | 865 | 59.981996 s | 59.981893 s | Yes | Yes |
| Strix RAW_IMU | 3,007 | 60.119942 s | 60.085710 s | Yes | Yes |

### 4.1 Recorded interval statistics

| Stream | Median sensor interval | P95 sensor interval | Median host interval | P95 host interval |
|---|---:|---:|---:|---:|
| RGB | 66.7212 ms | 133.4376 ms | 66.7312 ms | 133.1712 ms |
| Depth | 66.7212 ms | 66.7351 ms | 66.7365 ms | 67.7958 ms |
| Strix RAW_IMU | 20.0030 ms | 20.3130 ms | 19.9814 ms | 21.5935 ms |

Interpretation:
- All six timestamp sequences are strictly increasing.
- RGB has a wider interval distribution than depth; its P95 sensor interval is approximately twice its median.
- Depth intervals are comparatively consistent in this recording.
- Strix sensor timestamp cadence is approximately 50 Hz. Host receive intervals show greater variability than sensor-reported intervals.
- These are observations of recorded timestamp cadence, not independent verification of physical sensor sampling accuracy.

## 5. Offset evidence assessment — B4.3.4

The following paired timestamp calculations were previously performed:

| Comparison | Samples | Minimum | Median | Mean | P95 | Maximum |
|---|---:|---:|---:|---:|---:|---:|
| Estimated host wall time minus RGB header | 836 | 62.280 ms | 63.737 ms | 63.763 ms | 64.137 ms | 65.572 ms |
| Estimated host wall time minus depth header | 865 | 63.848 ms | 65.543 ms | 65.548 ms | 66.066 ms | 67.083 ms |
| Strix host receive time minus sensor timestamp | 3,007 | 4,471.767 ms | 4,508.785 ms | 4,508.824 ms | 4,541.474 ms | 4,579.186 ms |

These are apparent timestamp differences, not calibrated sensor clock offsets.

The candidate logger source files sample the capture-start monotonic clock first and wall clock immediately afterward:
- `time.monotonic_ns()`
- `datetime.now().astimezone().isoformat()`

The two samples are not atomic, and their interval is not recorded. Only a monotonic capture-end timestamp is recorded. The exact logger version that generated the October 26 dataset has not been conclusively identified.

No independent common camera–IMU hardware clock reference or shared timestamp trigger was established. Camera callback and IMU receive timestamps represent different host observation events.

**B4.3.4 conclusion:** Numerical differences are available, but a true sensor clock offset is not verified.

## 6. Drift evidence assessment — B4.3.5

The endpoint elapsed-time differences are:

| Stream | Host elapsed minus sensor elapsed |
|---|---:|
| RGB | -0.011 ms |
| Depth | -0.103 ms |
| Strix RAW_IMU | -34.232 ms |

The corresponding endpoint ratios can be described numerically, but they are not calibrated drift estimates:
- RGB: approximately -0.183 ppm
- Depth: approximately -1.717 ppm
- Strix RAW_IMU: approximately -569.395 ppm

These values compare elapsed host observation time with elapsed sensor-reported time. They do not isolate sensor oscillator rate error. In particular, the Strix comparison includes message delivery, buffering and software receive-observation effects. Camera comparisons include camera/driver pipeline and callback-observation effects.

The executed script reported timestamp ordering and interval statistics. It did **not** perform the ordinary least-squares regression discussed in the initial plan. No regression slope or regression-derived ppm result is claimed in this record.

**B4.3.5 conclusion:** Timestamp ordering and cadence are characterized for the existing dataset. Relative camera–Strix clock drift, individual clock-rate accuracy, and physical measurement-time drift remain unestablished.

## 7. Uncertainty and limitations — B4.3.6

1. The active D455 timestamp domain (hardware, system or global time) during this capture is unknown.
2. D455 header timestamp exposure/readout semantics are not verified.
3. Strix `RAW_IMU.time_usec` clock origin is not firmware-confirmed.
4. Strix timestamp-to-physical-IMU-measurement semantics are not verified.
5. Camera host time is recorded at ROS callback entry, not at a verified exposure event.
6. IMU host time is recorded after `recv_match()` returns, not at a verified physical sampling event.
7. Camera pipeline, transport, serial buffering, scheduling and callback delays have not been separately measured.
8. The capture-start wall and monotonic timestamps are sampled sequentially rather than atomically; the interval is not recorded.
9. Candidate source-code matches do not conclusively identify the exact logger version used for the dataset.
10. A single approximately 60-second recording does not establish long-term clock-rate stability.
11. Timestamp interval variation and endpoint elapsed-time differences cannot, by themselves, distinguish oscillator drift from variable observation delay.
12. The existing RGB–depth software association result is not evidence of camera–IMU hardware synchronization.

## 8. Final B4.3 conclusion

**Overall status: Complete as an evidence review, with technical limitations.**

The available dataset establishes:
- Monotonic recorded timestamp sequences for RGB, depth and Strix IMU.
- Approximately 50 Hz Strix timestamp cadence.
- Recorded RGB and depth timestamp interval behaviour.
- Numerical apparent timestamp differences between sensor-reported timestamps and host observation timestamps.

The available dataset does not establish:
- Verified camera or Strix clock origins in a common time domain.
- Calibrated camera–host or Strix–host clock mappings.
- True camera–IMU clock offset.
- Relative clock drift or long-term clock-rate accuracy.
- Physical exposure-to-IMU-measurement temporal alignment.
- Hardware synchronization between camera and IMU.

No unverified offset or drift value should be used as a calibrated correction.

## 9. Evidence-preservation note

This assessment uses the existing October 26 dataset and previously reviewed source/metadata evidence. No new sensor capture was performed. The existing RGB–depth association analysis was not repeated.

**Deliverable:** `SM_B4_3_Clock_Domain_Relationship.md`

bash 
```
ros2 launch realsense2_camera rs_launch.py \
    enable_color:=true \
    enable_depth:=true \
    enable_infra1:=false \
    enable_infra2:=false \
    enable_gyro:=true \
    enable_accel:=true

source /opt/ros/humble/setup.bash

source /opt/ros/humble/setup.bash
python3 ~/strix_imu_test.py


ros2 run mavros mavros_node \
  --ros-args \
  -r __ns:=/uas1 \
  -p fcu_url:=/dev/serial/by-id/usb-ArduPilot_Zerodrag_Strix_R0.1_310032001551343131393036-if00:115200 \
  -p fcu_protocol:=v2.0 \
  -p tgt_system:=1 \
  -p tgt_component:=1 \
  --params-file /opt/ros/humble/share/mavros/launch/apm_config.yaml

  ros2 topic hz /uas1/mavros/imu/data_raw
  ros2 topic echo /camera/camera/depth/camera_info --once
  

cd ~/Autonomous-ISR-VTOL && 
cat ros_WS/src/sensor_node/sensor_node/health/sensor_health_monitor.py

```

1. Sensor Acquisition
Existing sensor drivers and recorded data interfaces


2. Data Integrity and Diagnostics

Message validity, timestamps, missing data, data formats and metadata


3. Calibration and Configuration Registry

Calibration provenance, sensor identity, configuration versioning and frame documentation


4. Sensor Health and Diagnostics

Health states, fault history, stale-data reporting and recovery records


5. Validation and Dataset Management

Offline analysis, reproducibility, acceptance reports and evidence archive


verified status
===== /dev/ttyACM0 =====
ID_VENDOR=ArduPilot
ID_VENDOR_ENC=ArduPilot
ID_VENDOR_ID=1209
ID_MODEL=Zerodrag_Strix_R0.1
ID_MODEL_ENC=Zerodrag_Strix_R0.1
ID_MODEL_ID=5740
ID_SERIAL=ArduPilot_Zerodrag_Strix_R0.1_310032001551343131393036
ID_SERIAL_SHORT=310032001551343131393036
ID_USB_INTERFACE_NUM=00
ID_VENDOR_FROM_DATABASE=Generic
===== /dev/ttyACM1 =====
ID_VENDOR=ArduPilot
ID_VENDOR_ENC=ArduPilot
ID_VENDOR_ID=1209
ID_MODEL=Zerodrag_Strix_R0.1
ID_MODEL_ENC=Zerodrag_Strix_R0.1
ID_MODEL_ID=5740
ID_SERIAL=ArduPilot_Zerodrag_Strix_R0.1_310032001551343131393036
ID_SERIAL_SHORT=310032001551343131393036
ID_USB_INTERFACE_NUM=02
ID_VENDOR_FROM_DATABASE=Generic

/uas1/mavros/param/pull
/uas1/mavros/param/set
/uas1/mavros/param/event

param_id: GPS1_COM_PORT
value:
  type: 2
  integer_value: 1
param_index: 479
param_count: 1248