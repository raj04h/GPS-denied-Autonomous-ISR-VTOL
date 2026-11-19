# B4.5.1 — Synchronization Requirements and Acceptance Criteria

**Project:** Autonomous ISR Sensor Management  
**Hardware:** Intel RealSense D455 + Strix Flight Controller  
**Compute:** NVIDIA Jetson Orin NX  
**Work Package:** B4.5 — Synchronization Acceptance Evidence  
**Status:** Draft for engineering review

---

## 1. Objective

Define measurable requirements and acceptance criteria for evaluating timestamp integrity, sampling consistency, data continuity, clock-domain relationships and camera–IMU synchronization.

The purpose is to establish which synchronization properties are supported by existing evidence and which remain unverified.

This document defines requirements. It does not certify that the system currently satisfies them.

## 2. Approved nominal sensor rates

The following nominal rates are approved as B4.5 operating requirements.

| Sensor stream | Nominal rate | Nominal period |
|---|---:|---:|
| D455 RGB | 30 Hz | 33.333 ms |
| D455 Depth | 30 Hz | 33.333 ms |
| Strix RAW_IMU | 50 Hz | 20 ms |

**Important distinction:** These are target operating rates. They are not measured performance results. Actual stream frequency and interval distributions must be evaluated independently.

## 3. Synchronization requirements

### SYNC-01 — Timestamp integrity

**Objective:** Establish that timestamps within each sensor stream are internally consistent.

Acceptance evidence:
- Timestamp sequence is monotonic.
- Duplicate timestamps are counted.
- Regressing timestamps are identified.
- Timestamp units and provenance are documented.
- Unknown timestamp semantics are explicitly recorded.

A monotonic sequence alone does not establish correct measurement timing.

### SYNC-02 — Sampling consistency

**Objective:** Evaluate observed sensor cadence against the approved nominal rates.

Acceptance evidence:
- Observed frequency is calculated separately for RGB, Depth and RAW_IMU.
- Mean, median, minimum and maximum intervals are reported.
- Interval distribution is reported.
- Intervals exceeding 100 ms and 500 ms are identified for anomaly review.
- Requested/configured rate is distinguished from observed rate.

No numerical frequency tolerance has been approved. Therefore, a measured rate cannot receive an unconditional conformance PASS until an allowable deviation is formally defined.

### SYNC-03 — Data continuity

**Objective:** Identify missing samples, long intervals and timestamp discontinuities.

Acceptance evidence:
- Duplicate and regressing timestamps are identified.
- Long intervals are counted and listed.
- Large timestamp jumps are flagged.
- Potential discontinuities are classified without assuming their cause.
- Capture interruptions are distinguished from timestamp anomalies wherever evidence permits.

No maximum allowable data gap has yet been specified.

### SYNC-04 — Common host-clock comparison

**Objective:** Determine whether camera and IMU host-observation events can be compared using a common clock.

Acceptance evidence:
- Host timestamp clock source is identified.
- Monotonic clock usage is verified.
- Timestamp capture location in the software pipeline is documented.
- Camera callback-entry and IMU receive-event semantics are distinguished.
- Capture-start and capture-end timestamp provenance is documented.

Host arrival timestamps describe software-observed events. They do not independently establish the physical sensor measurement instant.

### SYNC-05 — Sensor clock-domain relationship

**Objective:** Establish whether camera and IMU timestamp domains have a defensible relationship.

Acceptance evidence:
- Timestamp source and units are documented for each stream.
- Clock-domain assumptions are identified.
- Any conversion or offset mapping is supported by evidence.
- Unverified boot-time or epoch-time assumptions remain explicitly marked unknown.

### SYNC-06 — Physical measurement-time synchronization

**Objective:** Establish whether camera and IMU measurements are synchronized at the physical acquisition level.

Acceptance evidence must include independently supported measurement-time evidence, such as:
- Verified hardware synchronization or trigger evidence.
- A validated common-clock relationship.
- Independently validated temporal calibration evidence with stated uncertainty.

Monotonic timestamps, matching nominal frequencies, host arrival timing, software message association and RGB/depth pairing are not sufficient by themselves.

## 4. Acceptance classification

| Classification | Meaning |
|---|---|
| PASS | Available evidence satisfies the defined requirement. |
| CONDITIONAL | Partial evidence exists, but limitations prevent full acceptance. |
| NOT DEMONSTRATED | Required evidence is absent or insufficient. |

Each requirement must be assessed independently. A PASS for timestamp integrity does not imply a PASS for physical synchronization.

## 5. Existing evidence to be reused

The October 26 dataset is the primary dataset for this work package:

`~/Autonomous-ISR-VTOL/data/concurrent_sensor_captures/20261026_212010/`

Expected files:
- `rgb_timing.csv`
- `depth_timing.csv`
- `imu.csv`
- `session_metadata.json`
- `sm02b_association_10ms/matched_pairs.csv`
- `sm02b_association_10ms/unmatched_frames.csv`
- `sm02b_association_10ms/summary.json`

Historical B4.1–B4.4 reports will be reused. Previously completed analyses will not be repeated without a specific evidence gap.

### Historical observations requiring consideration

**Camera:** One historical capture reported approximately 29.3 Hz, while another requested at 30 Hz reported approximately 14.99 Hz. Both showed long intervals despite monotonic timestamps.

**IMU:** Historical reports showed approximately 20 ms median intervals but also unusually large timestamp intervals. Their cause was not established.

**Cross-sensor:** Existing RGB/depth association evidence came from camera data. Independent camera and IMU capture sessions cannot establish camera–IMU synchronization.

These historical observations are not substitutes for reviewing the October 26 dataset.

## 6. Acceptance matrix

| ID | Requirement | Required evidence | Initial acceptance rule |
|---|---|---|---|
| SYNC-01 | Timestamp integrity | Per-stream timestamp sequence | No unexplained duplicates or regressions |
| SYNC-02 | Sampling consistency | Frequency and interval statistics | Compare against nominal rates; tolerance TBD |
| SYNC-03 | Data continuity | Gap and discontinuity analysis | All observed anomalies identified and classified |
| SYNC-04 | Common host clock | Clock source and timestamp capture semantics | Common monotonic clock provenance verified |
| SYNC-05 | Clock-domain relationship | Sensor timestamp provenance and mapping evidence | Defensible mapping established or limitation documented |
| SYNC-06 | Physical synchronization | Independent measurement-time evidence | Measurement-time relationship independently demonstrated |

## 7. Parameters not yet specified

The following limits must not be invented during evidence review:

- Maximum allowable camera interval deviation.
- Maximum allowable IMU interval deviation.
- Maximum allowable jitter.
- Maximum allowable data gap.
- Maximum camera–IMU synchronization error.
- Maximum temporal calibration uncertainty.
- Maximum acceptable end-to-end timestamp latency.

These require system-level requirements and a justified engineering basis before numerical acceptance limits can be assigned.

## 8. Execution sequence

| Checkpoint | Activity | Deliverable |
|---|---|---|
| B4.5.1 | Requirements and acceptance criteria | This document |
| B4.5.2 | Camera timestamp integrity | Camera timestamp report |
| B4.5.3 | IMU timestamp integrity | IMU timestamp report |
| B4.5.4 | Cross-sensor synchronization evidence | Cross-sensor report |
| B4.5.5 | Consolidated acceptance | Final synchronization acceptance report |

## 9. Constraints

1. Existing evidence first.
2. No repetition of completed B4.1–B4.4 work.
3. One checkpoint at a time.
4. Unknown information remains explicitly unknown.
5. No unnecessary sensor-driver or pipeline changes.
6. Every conclusion must be traceable to recorded evidence.
7. Physical synchronization must not be inferred from software arrival timestamps.

## 10. B4.5.1 completion status

**Nominal rates:** Approved.

**Requirements structure:** Defined.

**Acceptance classifications:** Defined.

**Unspecified tolerances:** Retained as TBD.

**Document status:** Draft for engineering review. Formal B4.5.1 closure requires review of the criteria and approval of any remaining TBD acceptance limits.

---

**Next checkpoint:** B4.5.2 — Camera Timestamp Integrity.

The next review will use the existing October 26 camera timing evidence first.