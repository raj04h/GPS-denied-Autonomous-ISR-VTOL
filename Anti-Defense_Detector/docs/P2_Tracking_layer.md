# P2 — Visual Tracking Layer

## Development Documentation

**Project:** GPS-Denied Autonomous ISR Drone System  
**Document:** `tracking_layer.md`  
**Phase:** P2 — Visual Object Tracking  
**Status:** Development documentation  
**Scope note:** This document records the tracking layer's intended architecture and development process. It does not certify that every listed feature is implemented or tested.

---

## 1. Purpose

The Tracking Layer consumes frame-by-frame detections from the Perception/Detection Layer (P1) and maintains object identities across consecutive frames. It associates detections over time, updates track states, manages track lifecycles, and produces structured tracking output for visualization, replay, and downstream analysis.

The layer must remain independent of detector-specific model code. It should consume a documented detection contract and produce a documented track contract.

Tracking is an image-space observation function. It does not, by itself, establish world coordinates, identify an object's intent, determine threat level, or make navigation, engagement, or weapon-control decisions.

## 2. Objectives

### 2.1 Primary objectives

- Consume P1 detection records in a stable, documented format.
- Associate detections across frames and maintain persistent track IDs where association is sufficiently reliable.
- Support tracker implementations behind a common interface.
- Support detector-driven multi-object tracking (MOT).
- Support user-selected object tracking where the UI/application supplies a valid selection.
- Preserve the distinction between detector observations and tracker estimates.
- Handle missed detections, temporary occlusion, new tracks, and track termination through explicit lifecycle states.
- Validate frame metadata, image dimensions, timestamps, bounding boxes, and detection-to-frame alignment.
- Produce machine-readable JSONL output and optional visualization.
- Support repeatable testing through recorded video and detection-log replay.
- Keep configuration, I/O, tracking algorithms, visualization, and orchestration in separate modules.

### 2.2 Quality objectives

The implementation should be measurable against:

- **Identity continuity:** track IDs remain stable when the evidence supports continuity.
- **Association quality:** incorrect matches and duplicate tracks are measured on a labelled evaluation set.
- **Recovery:** behavior after short occlusions and missed detections is tested.
- **Latency:** per-frame processing time and end-to-end delay are recorded.
- **Robustness:** malformed records, empty detections, end-of-file, and frame-size mismatches are handled explicitly.
- **Reproducibility:** a run can be repeated with the same input, configuration, and tracker version.
- **Observability:** logs report counts, errors, processing time, and lifecycle transitions without silently hiding failures.

Targets for accuracy, latency, frame rate, and resource use must be set from the actual camera, hardware, video, and evaluation requirements. Do not treat illustrative values as acceptance thresholds.

## 3. Scope and Responsibilities

### In scope

- Read a video frame and its frame metadata.
- Read or receive P1 detections for the corresponding frame.
- Normalize detections into a tracker-independent representation.
- Validate coordinate convention and image dimensions.
- Update the selected tracker once per frame.
- Maintain track IDs, bounding boxes, confidence/quality metadata, and lifecycle state.
- Support MOT from P1 detections.
- Provide an interface for application-level user selection of one or more visible detections/tracks, subject to the capabilities of the configured tracker.
- Buffer short track histories for trajectory visualization and diagnostics.
- Write structured per-frame tracking records.
- Display annotated frames for development and evaluation.
- Replay existing detection JSONL logs against the matching video.
- Record performance and validation statistics.

### Out of scope

The Tracking Layer does not own:

- Object detection model inference or detector training.
- Scene graphs or high-level scene interpretation.
- GPS-denied localization, visual odometry, SLAM, or world-coordinate estimation.
- IMU/GNSS fusion or navigation-state estimation.
- Flight-control commands or autonomous route planning.
- Threat scoring, target prioritization, engagement logic, or weapon control.
- Claims of identity or intent that cannot be supported by the visual observations.

These responsibilities, if needed for a broader system, require separate interfaces, validation, and safety review.

## 4. High-Level Processing Flow

```text
Video / Camera Frames
        |
        v
Frame Source --------------------------+
        |                              |
        v                              |
Frame ID + Timestamp + Image           |
        |                              |
        +------------------------------+
                                       |
P1 Detection JSONL / Detection Stream  |
        |                              |
        v                              |
Detection Adapter                      |
        |                              |
        v                              |
Schema + Frame + Resolution Validation |
        |                              |
        v                              |
Tracking Pipeline <--------------------+
        |
        v
Tracker Interface
        |
        +--> BoT-SORT / configured MOT backend
        +--> MOSSE / selected single-object tracker (if enabled)
        |
        v
Track Lifecycle + Track State
        |
        +--> Track History Buffer
        +--> JSONL Output Writer
        +--> Optional Visualization
        +--> Metrics / Diagnostics
```

The actual backend and enabled modes are determined by the code and configuration. This diagram describes the intended separation of responsibilities, not a claim that every path is implemented.

## 5. Current Project Structure

The development structure discussed for the tracking layer is:

```text
Autonomous-ISR-VTOL/
└── Anti-Defense_Detector/
    ├── asset/
    │   └── drone_testing.mp4
    ├── data/
    │   └── output/
    │       └── eo_perception_v1.jsonl
    ├── detection_Layer/
    │   └── ... P1 implementation ...
    ├── tracking_layer/
    │   ├── __init__.py
    │   ├── main_tracking.py
    │   ├── config.yaml
    │   ├── tracking_types.py
    │   ├── detection_adapter.py
    │   ├── botsort_tracker.py
    │   ├── tracking_pipeline.py
    │   ├── trajectory_buffer.py
    │   ├── output_writer.py
    │   └── jsonl_replay.py
    └── tracking_output.jsonl
```

This reflects the working structure described during development. Confirm the current filesystem before adding, renaming, or deleting files.

## 6. Module Responsibilities

### 6.1 `main_tracking.py`

Application entry point. It should:

1. Resolve project-relative paths.
2. Load runtime configuration and command-line overrides.
3. Run focused smoke tests when requested.
4. Open the selected video and detection source.
5. Construct the adapter, tracker backend, pipeline, and output writer.
6. Run the processing/visualization loop.
7. Report errors and performance summaries.
8. Release video, window, and file resources reliably.

The default video, P1 JSONL, and output paths should be explicit. When the video changes, the detection log must correspond to the same footage and compatible frame indexing/resolution.

### 6.2 `tracking_types.py`

Defines the shared data contracts used by the tracking modules. Keep these types independent of the selected tracker library.

Expected concepts include:

- `Detection`: frame ID, timestamp, class information, confidence, bounding box, and source metadata when available.
- `Track`: stable track ID, bounding box, class information when available, state, age/hit/miss metadata, and optional tracker quality.
- `FrameDetections`: frame metadata plus zero or more normalized detections.
- `TrackState`: explicit lifecycle values such as tentative, confirmed, lost, and terminated, adapted to the implementation.

Types should validate values at system boundaries where practical. Avoid duplicating the same field with conflicting meanings across modules.

### 6.3 `detection_adapter.py`

Converts P1 JSONL records into the shared detection contract. It should:

- Parse one JSON object per line.
- Normalize the P1 schema into the tracking schema.
- Preserve frame IDs and timestamps.
- Normalize bounding boxes to one convention, preferably pixel-space `xyxy` (`x1, y1, x2, y2`).
- Carry image width and height when supplied.
- Handle empty-detection frames.
- Reject or clearly report malformed records.
- Avoid silently changing coordinates or frame IDs.

The adapter must not assume that a detection file matches an arbitrary video. It should validate frame association and dimensions.

### 6.4 `botsort_tracker.py`

Wraps the configured BoT-SORT backend behind the project tracker interface. It should:

- Convert normalized detections to the backend's required input format.
- Call the backend once for each valid frame.
- Convert backend results into project `Track` objects.
- Keep third-party-specific types inside the wrapper.
- Expose relevant backend configuration through `config.yaml`.
- Handle empty detection sets according to the backend API.
- Report initialization and runtime errors clearly.

Library-specific input/output conventions must be checked against the installed version. Do not assume that a library's box order, confidence column, class column, or empty-input behavior matches the project's schema.

### 6.5 Tracker interface and single-object mode

A tracker interface should make backend substitution possible without changing the pipeline. If a single-object tracker such as MOSSE is enabled, keep its initialization/update contract separate from MOT association.

The application layer may pass a user selection using a documented selection event, such as a frame ID and bounding box or a valid track ID. The tracking layer should validate that selection against the current frame and tracker capabilities, then return a clear result indicating whether the selection was accepted.

Do not treat a detection's array position as a persistent identity. Array ordering may change between frames. A selection should refer to a frame-scoped detection identifier or a track ID, where available.

### 6.6 `tracking_pipeline.py`

Coordinates the frame-by-frame process. Its responsibilities are to:

1. Receive a frame and matching detection record.
2. Validate frame ID, timestamp, and image dimensions.
3. Normalize the detections.
4. Invoke the configured tracker.
5. update/emit the track states.
6. Update track-history buffers.
7. Send results to the output writer and optional visualization.
8. Record processing metrics and recoverable errors.
9. Stop cleanly at end-of-file or on user request.

The pipeline should not contain model-specific inference code or visualization-only logic.

### 6.7 `trajectory_buffer.py`

Maintains a bounded history of image-space positions for each active track. It should:

- Store a configured number of recent points.
- Associate history with track IDs.
- Remove history when a track is terminated or after a configured retention period.
- Support visualization and diagnostic exports.
- Avoid unbounded memory growth.

The history is an image-space trace, not a world-space trajectory or a navigation estimate.

### 6.8 `output_writer.py`

Writes machine-readable tracking output, preferably one JSON object per line. It should:

- Create output directories when configured to do so.
- Write a stable schema.
- Record frame metadata and zero or more tracks.
- Serialize numeric values consistently.
- Flush/close files safely.
- Report write failures rather than silently discarding output.

### 6.9 `jsonl_replay.py`

Supports deterministic replay of a saved P1 detection log against the matching video. It should:

- Parse JSONL records in a controlled way.
- Detect missing, duplicate, or out-of-order frame IDs where applicable.
- Report frame gaps and parse errors.
- Preserve source timestamps.
- Avoid silently reusing one detection record for the wrong frame.
- Support a bounded frame range for repeatable debugging.

### 6.10 `config.yaml`

Holds runtime parameters separately from algorithm code, including:

- Input video path and detection-log path.
- Output JSONL path.
- Display and output options.
- Tracker backend and backend parameters.
- Track-history length.
- Frame limits for testing.
- Logging level.
- Optional performance instrumentation.

Use paths relative to the project root where possible. Do not store credentials or sensitive stream URLs in a committed configuration file.

## 7. Input Contract and Synchronization

The tracking pipeline needs two aligned inputs:

1. **Video frame:** image pixels, frame ID/index, timestamp, width, and height.
2. **P1 detections:** zero or more detections associated with that exact frame.

The input sources must refer to the same recording and consistent frame indexing. If the video is replaced, regenerated, cropped, resized, or sampled at a different rate, regenerate the P1 detection log or apply a documented, verified coordinate transform.

### Resolution mismatch example

A video frame of `768 × 432` and a detection record declaring `1280 × 720` are not automatically compatible. A dimension check should fail clearly unless the pipeline has a verified transformation policy.

If—and only if—the detections represent the same image content resized uniformly from `1280 × 720` to `768 × 432`, the scale factors are:

```text
scale_x = 768 / 1280 = 0.6
scale_y = 432 / 720  = 0.6
```

Each coordinate can then be transformed using the corresponding axis scale. This is not appropriate for a different video, a different crop, different frame timing, or detections produced from different content. The preferred development workflow is to generate a fresh P1 JSONL file from the exact video being tracked.

### Required validation

- Frame ID and timestamp are present or explicitly derived by a documented policy.
- Bounding boxes use a single convention and valid numeric values.
- Box coordinates fall within, or are explicitly clipped to, the frame bounds.
- Image dimensions agree or a verified transform is configured.
- Detections are paired with the correct frame.
- Empty detection frames are represented explicitly, not omitted in a way that shifts alignment.

## 8. Tracking Data Contract

The exact schema must be implemented in `tracking_types.py` and used by all modules. The following is illustrative only:

```json
{
  "frame_id": 125,
  "timestamp": 12.5,
  "image_width": 768,
  "image_height": 432,
  "tracks": [
    {
      "track_id": 7,
      "bbox_xyxy": [252, 108, 390, 216],
      "class_id": 2,
      "class_name": "vehicle",
      "confidence": 0.91,
      "state": "confirmed"
    }
  ]
}
```

These values are examples, not measured model output. Optional fields should be omitted or set to `null` consistently when unavailable. Do not label a track confidence as detector confidence unless the source and meaning are explicit.

### Contract rules

- Use one bounding-box convention throughout the pipeline.
- Distinguish raw detections from tracker-produced states.
- Preserve source frame IDs and timestamps.
- Do not promise persistent identity when association is uncertain.
- Define how tentative, confirmed, lost, and terminated tracks are serialized.
- Document whether lost tracks are emitted for a limited period or omitted from the visible output.

## 9. Track Lifecycle

Use explicit lifecycle semantics rather than relying only on whether a box appears in a frame.

- **Tentative:** a candidate track has been created but has not met the confirmation rule.
- **Confirmed:** the tracker has sufficient evidence to maintain the track under its configured rules.
- **Lost:** a previously active track was not matched in the current frame but may be recoverable.
- **Terminated:** the track is no longer maintained by the tracker.

Exact transitions, maximum missed-frame limits, and confirmation thresholds are backend-dependent configuration items. They must be documented and tested against the installed tracker implementation.

A lost track should not be presented as a current detection. Visualization should distinguish current observations from predictions or stale track states.

## 10. Output Artifacts

Expected development outputs include:

1. **Annotated display:** optional preview showing boxes, track IDs, state, and recent image-space history.
2. **Tracking JSONL:** one record per processed frame, including frames with no tracks.
3. **Run diagnostics:** input paths, configuration summary, frame counts, processing time, errors, and termination reason.
4. **Evaluation results:** metrics computed on a labelled test set when one is available.

Discussed default paths:

```text
asset/drone_testing.mp4
data/output/eo_perception_v1.jsonl
tracking_output.jsonl
```

These are development defaults and must be overridden together when testing a different recording. The output filename alone does not establish that the run succeeded.

## 11. Configuration and Runtime Behavior

The configuration should make the following behavior explicit:

- Input video path.
- Matching P1 detection-log path.
- Output JSONL path.
- Tracker backend.
- Backend parameters.
- Display enable/disable.
- Optional frame limit.
- Track-history length.
- Logging verbosity.
- Optional performance measurements.

Command-line options should override defaults predictably. A no-argument launch from VS Code should use documented project-relative defaults. A `--check` or equivalent test mode should run checks without starting the full visualization loop.

Never silently continue after a critical frame-alignment or resolution error. Show the input paths and the offending frame ID in the error message.

## 12. Development Process and Milestones

### P2.1 — Freeze the contracts

- Inspect the actual P1 JSONL schema.
- Define `Detection`, `Track`, frame metadata, and lifecycle types.
- Fix the bounding-box convention and timestamp policy.
- Add schema-validation tests.

**Exit criterion:** sample P1 records can be parsed into normalized detections without ambiguous field meanings.

### P2.2 — Implement the detection adapter

- Parse JSONL line by line.
- Handle valid detections and empty frames.
- Detect malformed lines and frame gaps.
- Validate image dimensions and frame association.

**Exit criterion:** known-good records parse correctly and invalid/mismatched records fail with actionable messages.

### P2.3 — Integrate the tracker wrapper

- Confirm the installed backend version and API.
- Implement input conversion and output normalization.
- Test non-empty and empty detection frames.
- Keep backend-specific types inside the wrapper.

**Exit criterion:** the wrapper returns project-defined track records for a small, repeatable test sequence.

### P2.4 — Build the pipeline

- Connect video reading, replay, adapter, tracker, and output writer.
- Process frames in order.
- Handle end-of-file and user exit.
- Guarantee cleanup on exceptions.

**Exit criterion:** a short sample run completes and produces one output record per processed frame.

### P2.5 — Add lifecycle and history handling

- Define lifecycle transitions.
- Bound history memory.
- Test missed detections, temporary occlusion, and track termination.
- Ensure stale states are not drawn as current detections.

**Exit criterion:** lifecycle behavior is explicit and covered by deterministic tests.

### P2.6 — Add visualization and user selection interface

- Draw track boxes and IDs.
- Add a clear legend for current, tentative, and lost states.
- Define a frame-scoped selection event for single-object tracking, if enabled.
- Validate selection and report acceptance/rejection to the UI.

**Exit criterion:** the displayed state agrees with the serialized output, and invalid/stale selections are rejected safely.

### P2.7 — Add replay and output validation

- Replay the matching P1 JSONL with the corresponding video.
- Validate output schema and frame ordering.
- Test output paths, file errors, and resource cleanup.
- Ensure every processed frame is represented, including empty-track frames.

**Exit criterion:** a run can be reproduced from its recorded inputs and configuration.

### P2.8 — Measure performance and evaluate

- Record processing time and effective frame rate.
- Evaluate on representative labelled clips.
- Measure identity switches, fragmentation, false associations, and missed tracks where annotations permit.
- Test varying motion, scale, blur, occlusion, and camera movement.
- Record hardware, software versions, configuration, and limitations.

**Exit criterion:** performance claims are supported by recorded test results rather than visual inspection alone.

## 13. Testing Strategy

### Unit tests

- Bounding-box normalization and validation.
- P1 JSONL parsing.
- Missing and malformed fields.
- Frame ID/timestamp handling.
- Track lifecycle transitions.
- Bounded trajectory history.
- JSONL serialization and round-trip parsing.
- Resolution mismatch rejection.
- Empty-detection behavior.

### Integration tests

- Video + matching P1 JSONL + tracker backend.
- Short clip with no detections.
- Clip with intermittent detections.
- End-of-file and manual exit.
- Output directory missing or unwritable.
- Detection log for a different resolution.
- Detection log from a different recording.
- Repeat run with identical inputs and configuration.

### Evaluation metrics

Use an annotated dataset where available. Suitable tracking measures include:

- ID switches.
- Track fragmentation.
- False-positive and false-negative associations.
- IDF1 and HOTA, where the evaluation setup supports them.
- Processing latency and effective FPS.
- Track recovery behavior after temporary occlusion.

Metrics must be interpreted alongside the dataset, annotation policy, tracker configuration, and hardware. A successful preview window is not sufficient evidence of tracking accuracy.

## 14. Known Development Risks

- **Wrong detection log:** P1 records can be paired with a different video.
- **Resolution mismatch:** boxes can be invalid or shifted if dimensions differ.
- **Frame-index mismatch:** dropped frames or differing sampling rates can break synchronization.
- **Coordinate-convention mismatch:** `xyxy`, `xywh`, normalized coordinates, and backend-specific formats can be confused.
- **Backend API mismatch:** installed tracker versions may expect different array shapes or field ordering.
- **Unstable IDs:** occlusion, similar-looking objects, rapid motion, and camera motion can cause ID switches.
- **Unbounded history:** storing every point forever can increase memory use.
- **Misleading visualization:** predicted/lost tracks can be mistaken for current detections.
- **Unverified performance:** frame rate on one machine or clip may not generalize.

Each risk should have a visible failure mode, a test, and documented mitigation.

## 15. Definition of Done

The tracking-layer development scope is ready for evaluation when:

- The shared input/output contracts are documented and implemented.
- The P1 adapter validates frame alignment and dimensions.
- The configured tracker is wrapped behind a stable interface.
- The pipeline processes frames in order and handles empty detections.
- Track lifecycle states have explicit semantics.
- JSONL output is valid, stable, and parseable.
- Visualization corresponds to the serialized output.
- A different video cannot silently reuse an incompatible detection log.
- Unit and integration tests cover the critical paths.
- Performance and tracking quality are measured on representative data.
- Dependencies, configuration, test procedure, and known limitations are documented.

This checklist defines development acceptance criteria; it is not a claim that all criteria have already passed.

## 16. Boundary with Adjacent Layers

### P1 — Detection Layer to P2

P1 provides per-frame observations: class information, confidence, bounding boxes, frame metadata, and image dimensions where available.

P2 associates those observations across frames and emits track states. P2 should not need to load or invoke P1 detector models directly.

### P2 — Tracking Layer to downstream consumers

P2 provides image-space track IDs, boxes, lifecycle state, timestamps, and optional short history. Downstream consumers must account for track uncertainty and lifecycle state.

P2 output is not a localization solution: an image-space bounding box or trace does not provide a reliable world position, range, or navigation state on its own.

## 17. Key Design Principles

- Keep detector-specific parsing in the adapter.
- Keep tracker-library-specific behavior in backend wrappers.
- Use explicit shared data types and one coordinate convention.
- Keep configuration separate from algorithm code.
- Validate video/detection synchronization before tracking.
- Represent empty frames and track lifecycle transitions explicitly.
- Keep visualization separate from tracking logic.
- Bound memory and close resources reliably.
- Make errors actionable; do not silently repair incompatible inputs.
- Separate measured performance from intended performance.
- Keep tracking as an observation and continuity layer, not a decision or control layer.

---

**Document note:** This document follows the organization and level of detail of the supplied P1 development document and the tracking-layer structure discussed in the project. It records intended responsibilities and development milestones; current implementation status must be verified by running the code and tests.
"""

output_path = "/mnt/data/tracking_layer.md"
pypandoc.convert_text(
    content,
    to="md",
    format="md",
    outputfile=output_path,
    extra_args=["--standalone"]
)

print(f"Created: {output_path}")
