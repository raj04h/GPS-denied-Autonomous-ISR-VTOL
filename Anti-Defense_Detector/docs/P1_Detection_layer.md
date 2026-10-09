# P1 — Detection Layer
## Development Documentation

**Project:** GPS-Denied Autonomous ISR Drone System  
**Document:** `perception_layer.md`  
**Phase:** P1 — Perception / Object Detection  
**Status:** Development documentation

---

## 1. Purpose

The Perception Layer processes visual input and detects objects in each frame. It accepts video or camera frames, runs configured detection models, manages their outputs, combines detections where configured, and produces visual and machine-readable detection results.

This layer provides object-level observations to downstream software layers. It does not interpret the complete scene or make navigation decisions.

## 2. Scope and Responsibilities

### In scope

- Read frames from a video file, webcam, or RTSP stream.
- Run configured object-detection models.
- Standardize and manage detector results.
- Apply configured detection-fusion logic.
- Produce bounding-box visualizations.
- Write structured detection logs.
- Optionally save processed output video.
- Expose detection results to the next software layer.

### Out of scope

These are not responsibilities of P1:

- Scene-level interpretation or scene graphs.
- Object tracking across frames.
- Visual odometry, SLAM, or GPS-denied localization.
- IMU integration or multi-sensor fusion.
- Flight-control decisions or autonomous navigation.
- Engagement or weapon-control decisions.

These functions, if required, belong in separate downstream layers.

## 3. High-Level Processing Flow

```text
Video File / Webcam / RTSP
          |
          v
      VideoSource
          |
          v
   Frame Processing
          |
          v
    DetectionManager
      /    |    \
     v     v     v
  RF-DETR  Vehicle  Gun / Weapon
          Detectors
          |
          v
   Detection Fusion
          |
          v
  Detection Results + Bounding Boxes
          |
          +------> Display
          +------> Optional Output Video
          +------> Structured JSONL Log
          |
          v
   Downstream Layer Interface
```

The exact models enabled at runtime are controlled by the project configuration.

## 4. Current Project Structure

The structure discussed during development is:

```text
Autonomous-ISR-VTOL/
├── models/
│   ├── vehicle_model.pt
│   ├── gun_model.pt
│   └── weapon_model.pt
└── Anti-Defense_Detector/
    ├── asset/
    │   └── drone_testing.mp4
    ├── data/
    │   └── output/
    └── detection_Layer/
        ├── main_perception.py
        ├── bbox_detection.py
        ├── class_map.py
        ├── detector_interface.py
        ├── detection_manager.py
        ├── detection_fusion.py
        ├── Model_adaptor/
        │   ├── rfdetr_adaptor.py
        │   ├── vehicle_adaptor.py
        │   ├── gun_adaptor.py
        │   └── weapon_adaptor.py
        └── eo_processing/
            ├── eo_perception_pipeline.py
            ├── frame_processor.py
            └── video_source.py
```

This documents the structure discussed so far. File names or implementations may differ in the current working copy.

## 5. Module Responsibilities

### 5.1 `main_perception.py`

Acts as the application entry point. It is intended to:

- Define the input mode and input source.
- Configure model-weight paths and detector thresholds.
- Build the detection manager and fusion component.
- Configure display, output-video, and JSONL-log behavior.
- Instantiate and run the EO perception pipeline.

### 5.2 `eo_processing/video_source.py`

Provides the input abstraction for video files, local camera devices (such as a webcam), and RTSP streams. It yields frames with metadata including a frame identifier, timestamp, image, width, and height.

### 5.3 `eo_processing/frame_processor.py`

Provides per-frame processing support used by the EO pipeline. Its precise responsibilities should remain limited to frame-level processing rather than scene interpretation.

### 5.4 `eo_processing/eo_perception_pipeline.py`

Coordinates the processing loop. It is intended to:

1. Read an input frame.
2. Pass the frame to the detection manager.
3. Prepare the output frame and detection visualization.
4. Display results when display is enabled.
5. Save an output video when configured.
6. Write per-frame results to a JSONL log.
7. Handle resource cleanup when processing ends.

### 5.5 `detector_interface.py`

Defines the common interface expected from detector adapters so different models can be called through a consistent application-level contract.

### 5.6 `Model_adaptor/`

Contains adapters for the configured detection models. The models discussed in this project are RF-DETR, a vehicle detector, a gun detector, and a weapon detector. Model class names, supported labels, and inference details must come from each model's actual configuration and implementation.

### 5.7 `detection_manager.py`

Coordinates the configured detectors and manages their results through a common interface. It is the main component the pipeline uses to request detections for a frame.

### 5.8 `detection_fusion.py`

Combines or reconciles detections from multiple detector outputs according to the implemented fusion rules. The intended goal is to provide a consolidated set of detections rather than independent, uncoordinated outputs from every model.

### 5.9 `bbox_detection.py` and `class_map.py`

These files support bounding-box/detection handling and class-label mapping. Their exact contracts should follow the current source code.

## 6. Input Configuration

The application is intended to support three input modes:

| Mode | Source | Configuration concept |
|---|---|---|
| `video` | Recorded video file | Video path |
| `camera` | Local webcam or camera device | Camera index, commonly `0` |
| `rtsp` | Network camera stream | RTSP URL |

For initial development, `asset/drone_testing.mp4` provides a repeatable input source. Webcam or RTSP input can be selected through application configuration when the pipeline and source adapter are wired for that mode.

## 7. Detection Result Contract

The Detection Layer should provide a consistent representation of each detection. At minimum, downstream consumers need:

- Frame identifier.
- Frame timestamp.
- Class identifier or class name.
- Confidence score.
- Bounding-box coordinates.
- Image dimensions or enough context to interpret the coordinates.
- Optional source-detector information, where available.

Illustrative detection record:

```json
{
  "frame_id": 125,
  "timestamp": 12.5,
  "class_name": "vehicle",
  "confidence": 0.91,
  "bbox_xyxy": [420, 180, 650, 360],
  "image_width": 1280,
  "image_height": 720,
  "source_detector": "vehicle_detector"
}
```

The values are examples only, not results from a real model run. The project should define and consistently use one bounding-box convention, such as `[x1, y1, x2, y2]` in pixel coordinates.

## 8. Output Artifacts

The planned outputs are:

1. **Live display:** optional window showing the processed frame and detections.
2. **Processed video:** optional annotated video file.
3. **JSONL log:** structured, machine-readable per-frame detection records.
4. **Run summary:** aggregate processing statistics, if implemented by the pipeline.

Discussed default output names:

```text
data/output/eo_perception_v1_result.mp4
data/output/eo_perception_v1.jsonl
```

These are configuration defaults, not confirmation that the files have been generated.

## 9. Configuration Items

The application configuration discussed so far includes:

- `INPUT_MODE`: `video`, `camera`, or `rtsp`.
- `VIDEO_PATH`: path to a recorded video.
- `CAMERA_INDEX`: local camera index.
- `RTSP_URL`: network stream address.
- `DISPLAY`: enable or disable live display.
- `SAVE_OUTPUT_VIDEO`: enable or disable output-video writing.
- `MAX_FRAMES`: optional frame limit.
- `OUTPUT_DIR`: output directory.
- `OUTPUT_VIDEO`: output-video path.
- `OUTPUT_LOG`: JSONL log path.
- Model-weight paths for vehicle, gun, and weapon detectors.
- Per-detector confidence thresholds.
- Detection-fusion parameters.

Exact threshold values should remain configurable and treated as tunable parameters rather than universal values.

## 10. Development Milestones

### P1.1 — Input handling
Implement the common frame-source abstraction for recorded video, webcam, and RTSP input.

### P1.2 — Detector adapters
Provide a consistent calling interface for each configured model.

### P1.3 — Detection management
Coordinate detector execution and collect results in a common format.

### P1.4 — Detection fusion
Apply configured rules to combine overlapping or duplicate detections from different models.

### P1.5 — Frame pipeline
Connect source reading, inference, result handling, and visualization in one processing loop.

### P1.6 — Output handling
Support optional annotated-video output and structured JSONL records.

### P1.7 — Interface for downstream layers
Expose stable per-frame detection results so later layers do not depend directly on model-specific outputs.

These milestones describe the development scope. They do not certify that every feature has been implemented or tested in the current codebase.

## 11. Definition of Done — Development Scope

The P1 development scope is considered implemented when the code provides:

- A common frame-input interface.
- Adapters for selected detectors.
- A detection manager that invokes configured detectors.
- A fusion component connected to the detection flow.
- A frame-processing pipeline.
- Optional detection visualization.
- Optional processed-video output.
- Structured detection logging.
- A documented output contract for downstream consumers.

Runtime verification is separate from this document and is not claimed here.

## 12. Boundary with P2 — Scene Understanding

P1 ends with **object-level detections for each frame**.

P2 — Scene Understanding — consumes P1's structured detection output and organizes it into a scene-level representation. P2 should not need to load or directly call individual detection models.

P1 provides detected objects and their image-space locations. It does not determine the overall meaning of the scene.

## 13. Key Design Principles

- Keep model-specific code inside detector adapters.
- Keep input-source handling separate from detection logic.
- Use one consistent detection schema across models.
- Keep configuration separate from core processing logic.
- Make video writing and display optional.
- Keep P1 focused on per-frame object detection.
- Do not add tracking, localization, sensor fusion, or scene reasoning to this layer.

---

**Document note:** This document records the P1 development architecture and intended responsibilities based on the project discussion. It distinguishes intended behavior from implementation details that still need confirmation in the source code.