# SM-B4.4.5 — Final Camera–IMU Temporal Relationship Record

**Work package:** SM-B4.4.5  
**System under review:** Intel RealSense D455 + Strix IMU, Jetson Orin NX  
**Historical dataset:** 26 October 2026 concurrent sensor capture  
**Assessment basis:** Completed SM-B4.4.1 through SM-B4.4.4 evidence reviews  
**Status:** Complete with limitations

---

## 1. Purpose

Consolidate the available evidence concerning the temporal relationship between the D455 camera streams and the Strix IMU. Distinguish established observations from unverified assumptions and state what can and cannot be concluded from the reviewed dataset.

This record is an evidence assessment. It does not estimate a temporal offset, clock drift, or camera–IMU extrinsic transform.

## 2. Dataset and evidence reviewed

Dataset directory:

`~/Autonomous-ISR-VTOL/data/concurrent_sensor_captures/20261026_212010/`

Reviewed artifacts:
- `rgb_timing.csv`
- `depth_timing.csv`
- `imu.csv`
- `session_metadata.json`
- `sm02b_association_10ms/matched_pairs.csv`
- `sm02b_association_10ms/unmatched_frames.csv`
- `sm02b_association_10ms/summary.json`

The reviewed dataset contains timing records and metadata. Original RGB/depth image observations and a recorded combined camera–IMU rosbag/DB3/MCAP were not found in the reviewed dataset location.

## 3. Established evidence

### 3.1 Camera timing records

- RGB and depth timing records contain camera ROS header timestamps and Jetson monotonic callback timestamps.
- The camera header timestamp domain was not conclusively identified.
- The relationship between the header timestamp and physical exposure start, midpoint, or end was not established.
- RGB/depth software association used a 10 ms tolerance and produced 821 accepted pairs, 15 unmatched RGB frames, and 44 unmatched depth frames.
- This association result is software-level frame association evidence; it does not prove hardware exposure synchronization or camera–IMU synchronization.

### 3.2 Strix IMU timing records

- `imu.csv` contains `sensor_time_usec` and `host_receive_monotonic_ns`.
- `sensor_time_usec` is copied from MAVLink `RAW_IMU.time_usec`.
- The sequence contains 3007 samples and is strictly increasing.
- Recorded sensor-time elapsed duration is 60.119942 s; median sensor interval is 20.003 ms, consistent with approximately 50 Hz cadence.
- The actual clock origin and physical measurement-time semantics for this Strix device/firmware were not verified.
- Host receive time is a software observation after message receipt, not a direct measurement of the physical sensor sampling instant.

### 3.3 Host arrival-event relationship

The camera callback and IMU receive events were compared using Jetson monotonic timestamps.

Nearest-event absolute differences:
- RGB callback to Strix receive: median 4.723 ms, p95 9.572 ms, maximum 10.562 ms.
- Depth callback to Strix receive: median 5.062 ms, p95 9.570 ms, maximum 10.704 ms.

Signed nearest-event comparison:
- RGB: nearest IMU receive event preceded 349 camera callbacks (41.75%) and followed 487 (58.25%); median signed difference +2.574 ms.
- Depth: nearest IMU receive event preceded 332 camera callbacks (38.38%) and followed 533 (61.62%); median signed difference +1.617 ms.

Positive signed difference means the nearest Strix host receive event occurred after the camera callback. These are non-one-to-one arrival-event comparisons. They are not physical measurement-time correspondences and must not be interpreted as a calibrated temporal offset.

### 3.4 Conditional timestamp comparisons

Previously calculated conditional apparent differences:
- RGB camera header versus estimated host wall time: median 63.737 ms.
- Depth camera header versus estimated host wall time: median 65.543 ms.
- Strix sensor timestamp versus host receive time: median 4508.785 ms.

These values are conditional numerical comparisons. The camera and Strix timestamps have not been demonstrated to share a clock domain or equivalent measurement-time semantics. The values are not calibrated offsets and are not directly comparable as camera–IMU temporal offset estimates.

### 3.5 Clock-rate and interval evidence

- Camera and IMU timestamp sequences were observed to be monotonic in the reviewed records.
- Sensor and host interval statistics were measured separately.
- Endpoint elapsed-time differences and interval characteristics were documented in SM-B4.3.
- Clock domains and measurement-time semantics remain unverified; therefore the observed interval differences cannot isolate true relative clock-rate error or calibrated relative drift.

## 4. Calibration and frame evidence relevant to temporal interpretation

### 4.1 Camera calibration information

Live D455 RGB and depth `CameraInfo` messages were retrieved at 640 × 480. The RGB and depth streams publish distinct intrinsic parameter sets. These are current live driver values; independent accuracy validation and identity with the October 26 capture configuration were not established.

### 4.2 IMU publication and configuration

MAVROS IMU publication was observed at approximately 50 Hz. An observed message used `header.frame_id = base_link`. MAVROS frame parameters were:
- `base_link_frame_id = base_link`
- `map_frame_id = map`
- `odom_frame_id = odom`

The inspected custom Strix publisher specifies `strix_imu_link`. The custom publisher source showed no explicit bias, scale-factor, or axis correction in that application-level conversion path. This does not establish whether internal firmware calibration is present or absent.

### 4.3 TF evidence

The observed `/tf_static` output contained the RealSense camera frame hierarchy:
- `camera_link`
- `camera_depth_frame`
- `camera_depth_optical_frame`
- `camera_color_frame`
- `camera_color_optical_frame`

Neither `base_link` nor `strix_imu_link` appeared in the inspected static transform output. No dynamic `/tf` message was received during the five-second inspection. Therefore, no camera-to-IMU transform was demonstrated by the reviewed TF evidence.

Frame names and configured frame IDs do not establish the physical mounting relationship or calibrated camera–IMU extrinsics.

## 5. Final temporal relationship assessment

| Question | Finding |
|---|---|
| Are camera timestamp sequences available? | Yes |
| Is the Strix sensor timestamp sequence available? | Yes |
| Are Jetson host arrival timestamps available for both streams? | Yes |
| Can host arrival-event proximity be described? | Yes |
| Is the active camera timestamp clock domain confirmed? | No |
| Is camera exposure-time semantics confirmed? | No |
| Is Strix `time_usec` clock origin confirmed? | No |
| Is Strix physical measurement-time semantics confirmed? | No |
| Is a common camera–IMU measurement-time clock mapping validated? | No |
| Is relative camera–IMU clock drift established? | No |
| Is a calibrated camera–IMU temporal offset established? | No |
| Is a physical camera-to-IMU transform established? | No |
| Does the October 26 dataset support offline visual–inertial temporal calibration? | No |

## 6. Conclusion

**The camera–IMU measurement-time relationship is not established by the reviewed October 26 dataset.**

The evidence supports:
- Camera and IMU timestamp sequence inspection.
- Sampling-interval and cadence analysis.
- Jetson host arrival-event comparison.
- Software-level RGB/depth frame association.
- Identification of timestamp provenance, calibration, and TF evidence gaps.

The evidence does not support:
- A calibrated camera–IMU temporal offset.
- Verified relative clock drift between camera and IMU.
- Hardware exposure synchronization.
- Physical camera–IMU measurement-time correspondence.
- A validated camera-to-IMU extrinsic transform.

The October 26 dataset should be retained as timing-provenance and arrival-event evidence only. It should not be used to claim a calibrated temporal relationship.

## 7. Recommended disposition

1. Preserve the October 26 dataset and its timing reports as historical evidence; do not rewrite or reinterpret its timestamps.
2. Keep camera sensor timestamps, IMU sensor timestamps, and Jetson host arrival timestamps as distinct fields.
3. Treat the live CameraInfo values as current configuration evidence unless capture-time identity is independently demonstrated.
4. Treat MAVROS frame IDs as labels/configuration, not proof of physical sensor mounting or extrinsic calibration.
5. For any future offline calibration exercise, use a new dataset that preserves original visual observations, raw IMU measurements, timestamp provenance and semantics, capture configuration, calibration provenance, and validation evidence as specified in SM-B4.4.4.

## 8. Work package status

| Checkpoint | Status |
|---|---|
| B4.4.1 — Existing temporal evidence inventory | Complete |
| B4.4.2 — Measurement-time semantics review | Complete with limitations |
| B4.4.3 — Temporal relationship evidence assessment | Complete with limitations |
| B4.4.4 — Calibration applicability and limitations | Complete with limitations |
| B4.4.5 — Final camera–IMU temporal relationship record | Complete with limitations |

**Overall B4.4 status:** Evidence review complete. The physical camera–IMU temporal relationship remains unverified.

---

**Boundary:** This record reports only what is supported by the reviewed data and live observations. No calibration result, sensor synchronization guarantee, or physical camera–IMU transform is claimed.

# SM-B4.4.4 — Calibration Applicability and Limitations

**Work package:** SM-B4.4.4  
**Dataset reviewed:** 26 October 2026, D455 + Strix concurrent sensor capture  
**Status:** Evidence review complete with limitations  
**Decision:** Not suitable for defensible offline camera–IMU temporal calibration.

## 1. Purpose

Assess whether the existing October 26 dataset contains sufficient evidence for offline camera–IMU temporal calibration, identify limitations, and define the evidence a future calibration dataset must preserve. This is an applicability and data-quality assessment. It does not perform calibration, estimate a temporal offset, or infer an unobserved camera-to-IMU transform.

## 2. Applicability decision

The October 26 dataset is suitable for reviewing timestamp sequences, sensor arrival timing, sampling intervals, and software-level camera/IMU timing evidence.

It is not sufficient to estimate or independently validate a camera–IMU measurement-time offset. The dataset does not preserve the original visual observations needed for image-based temporal calibration. The physical measurement-time semantics and clock relationship of both sensor streams also remain unverified.

## 3. Evidence-based assessment

| Requirement | Available evidence | Assessment |
|---|---|---|
| Camera timestamp sequence | RGB and depth timing CSVs | Available |
| IMU timestamp sequence | Strix `imu.csv` | Available |
| Common host arrival-time reference | Jetson monotonic callback/receive timestamps | Available |
| Original RGB observations | No original image files in the reviewed dataset | Missing |
| Original depth observations | No original depth frames in the reviewed dataset | Missing |
| Recorded combined image–IMU stream | No rosbag/DB3/MCAP found in the reviewed data directory | Missing |
| Camera timestamp domain | Not conclusively identified | Unverified |
| Camera exposure-time semantics | Start/midpoint/end semantics not established | Unverified |
| Strix `time_usec` clock origin | Boot-relative is plausible, not confirmed | Unverified |
| Strix physical measurement-time semantics | Not established | Unverified |
| Camera and IMU clock mapping | No independently validated mapping | Missing |
| Camera intrinsic parameters | Live D455 CameraInfo retrieved | Available for current live configuration; historical capture association unverified |
| IMU intrinsic calibration | No independently measured bias, scale or noise validation | Insufficient |
| Camera-to-IMU extrinsics | No validated transform found | Missing |
| Capture-time configuration provenance | Incomplete | Insufficient |

### Interpretation

The existing host timestamps support arrival-event analysis on the Jetson monotonic clock. They cannot be substituted for camera exposure time or IMU measurement time.

## 4. Evidence already established

### 4.1 Camera timing

The reviewed October 26 dataset contains RGB and depth timing records with camera header timestamps and Jetson monotonic callback timestamps. The camera timestamp domain and the relationship between the header timestamp and physical exposure time were not conclusively established.

The separate RGB/depth software association analysis found 821 accepted pairs within a 10 ms tolerance, with 15 unmatched RGB frames and 44 unmatched depth frames. This is software-level association evidence; it does not establish hardware exposure synchronization or camera-to-IMU synchronization.

### 4.2 Strix IMU timing

The reviewed `imu.csv` contains `sensor_time_usec` and `host_receive_monotonic_ns`. The Strix timestamp sequence is strictly increasing and has approximately 50 Hz cadence. The timestamp field is copied from MAVLink `RAW_IMU.time_usec`.

The field's actual clock origin and physical measurement-time semantics for this device/firmware remain unverified. The host receive timestamp records software observation after message receipt, not the instant of physical IMU measurement.

### 4.3 Host arrival-time relationship

Camera callback and IMU receive events can be compared on the Jetson monotonic clock. The nearest-event results describe arrival-event proximity only. They are not one-to-one measurement correspondences and must not be interpreted as a calibrated camera–IMU offset.

### 4.4 Current camera calibration information

Live D455 RGB and depth `sensor_msgs/CameraInfo` messages were retrieved at 640 × 480. RGB and depth publish distinct intrinsic parameter sets. These values are evidence of the current live driver configuration; they have not been independently accuracy-validated or proven to match the October 26 capture configuration.

### 4.5 IMU publication and frame evidence

MAVROS IMU publication was observed at approximately 50 Hz. An observed IMU message used `header.frame_id = base_link`. MAVROS parameters were confirmed as:
- `base_link_frame_id = base_link`
- `map_frame_id = map`
- `odom_frame_id = odom`

The inspected custom publisher specifies `strix_imu_link`. The observed static TF tree contained only the RealSense camera frame hierarchy. No dynamic TF message was received during the five-second inspection, and no camera-to-IMU transform was demonstrated.

The published covariance values and a single observed acceleration sample do not independently establish IMU noise, bias, scale-factor accuracy, or calibration quality.

## 5. Why the existing dataset is insufficient

1. **No original visual observations:** Without the original RGB sequence (and associated depth observations where relevant), image-based visual/inertial temporal calibration cannot be performed or independently reviewed.
2. **Unverified camera time semantics:** A camera header timestamp is not automatically an exposure timestamp. Its active clock domain and exposure-time reference must be known.
3. **Unverified IMU time semantics:** The Strix `time_usec` value cannot be assumed to represent boot time, epoch time, or the precise physical measurement instant without device-specific evidence.
4. **No validated common clock mapping:** Host arrival timestamps allow arrival-event comparison, but do not independently reveal sensor clock offset or drift.
5. **Incomplete calibration provenance:** Current live CameraInfo values are not proven to be the values active during the historical capture. Independent IMU calibration evidence is also insufficient.
6. **No validated camera–IMU extrinsic relationship:** The available TF evidence does not establish the physical mounting transform between the camera and IMU.

Consequently, no defensible measurement-time offset, relative clock drift, or camera–IMU extrinsic transform should be calculated from this dataset.

## 6. Evidence a future offline calibration dataset must preserve

This is a data-preservation and metrology checklist, not a flight-control or navigation implementation.

### 6.1 Original sensor observations
- Original RGB images, without lossy re-encoding or frame omission.
- Original depth frames if depth is part of the calibration or validation scope.
- Complete IMU sample records, including raw sensor values and original device timestamps.
- Stable association between each observation and its original timestamp/sample identifier.
- Records of dropped, duplicated, rejected, or malformed observations.
- Original files retained unchanged, with file hashes or equivalent integrity records.

### 6.2 Timestamp provenance
For each sensor stream, preserve:
- Timestamp field name and data type.
- Timestamp source: hardware, device firmware, driver, middleware, or host.
- Clock domain and clock origin.
- Timestamp units and epoch/boot-time interpretation.
- Whether the timestamp denotes measurement time, exposure start, exposure midpoint, exposure end, message creation, or host receipt.
- Any timestamp conversion or rewriting performed by the driver or logger.
- Host monotonic receive/callback timestamp, recorded separately from the sensor timestamp.
- Clock reset, rollover, discontinuity, or synchronization events.

Do not merge sensor timestamps into a common timeline until the clock-domain relationship is supported by evidence.

### 6.3 Camera calibration provenance
Preserve the calibration data corresponding to the actual capture configuration:
- RGB and depth image dimensions and stream formats.
- Intrinsic matrices and distortion coefficients for each relevant camera stream.
- Distortion model and rectification/projection parameters.
- Camera-to-camera geometry where relevant.
- Calibration source, date, method, version, and validation record.
- Camera serial number, firmware, driver and SDK versions.
- Stream configuration, frame rate, exposure settings, and relevant synchronization settings.

A live CameraInfo message captured later should not be represented as historical capture-time calibration unless configuration identity is demonstrated.

### 6.4 IMU calibration provenance
Preserve:
- Device identity, board revision, sensor identity where available, and firmware version.
- Axis convention, axis mapping, handedness, and units.
- Accelerometer and gyroscope scale-factor and bias calibration records.
- Temperature conditions and any temperature compensation information.
- Noise and stability characterization, with measurement procedure and conditions.
- Covariance values together with their provenance and meaning.
- Any firmware-side or driver-side calibration and correction, including version and configuration.

A ROS message covariance field is not, by itself, independent evidence that the sensor's noise properties have been measured correctly.

### 6.5 Camera–IMU geometry provenance
Preserve:
- Defined camera and IMU coordinate frames and axis conventions.
- Camera-to-IMU rigid transform, including rotation and translation.
- Calibration method, calibration dataset identity, software/version, and result uncertainty or validation evidence.
- Physical mounting configuration and any subsequent changes.
- TF frame names and actual transform values used during the relevant recording.

Frame labels or configured frame IDs alone do not establish physical extrinsic calibration.

### 6.6 Acquisition and software provenance
Preserve a session manifest containing:
- Capture start/end times and the time zone or time standard used.
- Device serial numbers and firmware versions.
- Jetson model, operating system, ROS 2 distribution, and relevant package versions.
- RealSense SDK and ROS driver versions.
- MAVLink/MAVROS versions and relevant device configuration.
- Exact launch commands, parameter values, stream settings, and logger versions.
- Whether any other process accessed the same serial device during acquisition.
- Recording start/stop events, interruptions, and process errors.
- Original dataset paths, file sizes, hashes, and a machine-readable session summary.

### 6.7 Independent timing evidence
Preserve evidence that supports the relationship between sensor clocks and physical measurement events. This may include documented hardware synchronization signals or an independently characterized timing reference, where supported by the devices.

If timing is inferred from software timestamps, document observation points, clock domains, uncertainty, transport/processing delays, and assumptions. Do not describe host-arrival comparison as hardware synchronization.

### 6.8 Calibration data quality and validation evidence
Preserve records demonstrating that:
- Visual observations contain sufficient usable scene information for the selected calibration method.
- The IMU record has sufficient continuity and valid samples for the selected method.
- The recording contains informative motion and visual variation, rather than relying only on a static or uninformative segment.
- Timestamp sequences have been checked for regressions, duplicates, gaps, and discontinuities.
- The selected calibration method's assumptions are documented and applicable to the sensor configuration.
- The result is checked on independent data or through a separately justified validation procedure.
- Estimated parameters, uncertainty, residual/error summaries, rejected intervals, and limitations are retained.

The required motion and data-quality conditions depend on the selected calibration method; a dataset should not be declared adequate solely because it contains images and IMU samples.

## 7. Decision boundary

The October 26 dataset may be used for:
- Reviewing camera and IMU timestamp sequence integrity.
- Reviewing sampling intervals and observed cadence.
- Reviewing Jetson host arrival-event relationships.
- Documenting software-level RGB/depth association.
- Identifying timestamp provenance and calibration evidence gaps.

The October 26 dataset must not be used to claim:
- A calibrated camera–IMU temporal offset.
- Verified relative clock drift between camera and IMU.
- Hardware exposure synchronization.
- A validated physical camera-to-IMU transform.
- Independently validated camera intrinsics or IMU noise/bias characteristics for the historical capture configuration.

## 8. Final conclusion

**SM-B4.4.4.4 decision: Not suitable for offline camera–IMU temporal calibration.**

The October 26 dataset supports timing-provenance and arrival-event evidence review, but it lacks the original visual observations and validated measurement-time/clock-domain evidence required for defensible offline temporal calibration. The live D455 CameraInfo and MAVROS IMU observations add current configuration evidence, but do not repair the missing historical capture data or establish a camera-to-IMU extrinsic relationship.

A future calibration dataset must preserve original image/depth and IMU observations, timestamp provenance and semantics, device/configuration identity, camera and IMU calibration provenance, coordinate-frame/extrinsic evidence, acquisition metadata, independent timing evidence where available, and validation records.

**No temporal offset or camera–IMU extrinsic calibration result is claimed in this assessment.**

## 9. Work package status

| Checkpoint | Status |
|---|---|
| B4.4.4.1 — Existing calibration parameter inventory | Complete with limitations |
| B4.4.4.2 — Camera calibration evidence | Complete with limitations |
| B4.4.4.3 — Strix IMU calibration evidence | Evidence review complete with limitations |
| B4.4.4.4 — Offline temporal calibration applicability | Complete |
| B4.4.4.5 — Final applicability and limitations | Ready for consolidation |

**Overall B4.4.4 status:** Evidence review complete with limitations.

