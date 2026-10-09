# P2 — Multi-Object Tracking Layer

**Project:** Autonomous GPS-Denied ISR VTOL  
**Document:** `tracking_layer.md`  
**Purpose:** Define the software boundary between object detection and frame-to-frame track records.

> Scope: general-purpose video-perception tracking architecture. This document does not specify operational deployment, target prioritization, or mission/engagement logic.

## 1. Purpose

Detection answers: “What objects were detected in this frame?” Tracking answers: “Which detections across frames may belong to the same continuing object?”

P2 consumes normalized, timestamped detections and maintains temporary track identities and lifecycle state. It does not perform detection, metric depth estimation, camera localization, cross-sensor fusion, or persistent world-model storage.

## 2. Responsibilities

**In scope**
- Consume one normalized detection stream.
- Associate detections across frames.
- Assign session-scoped `track_id` values.
- Update track records when observations are associated.
- Represent tentative, confirmed, temporarily missing, and ended tracks.
- Emit structured track records per frame.
- Keep backend choice and lifecycle settings behind a stable interface.

**Out of scope**

| Responsibility | Owner |
|---|---|
| Frame capture and decoding | Video source / EO pipeline |
| Object detection and class prediction | P1 — Perception |
| Cross-sensor association and evidence fusion | Multi-Modal Fusion |
| UAV pose, velocity, camera ego-motion | State Estimation / VIO |
| Metric depth and relative 3D position | Depth / 3D Target State |
| Persistent terrain/object/event history | ISR World Model |
| Mission and flight-control decisions | Mission/C2 and flight-control stack |

## 3. Position in the HLD

```text
Video frame → P1 Detection → P2 Multi-Object Tracking
                                  |
                                  v
                       Frame-stamped track records
                                  |
                     +------------+-------------+
                     v                          v
               Depth / 3D                 ISR World Model
             (separate owner)             (separate owner)
```

The detailed HLD also contains Multi-Modal Fusion. Freeze whether P2 consumes P1 detections or fused observations before integration. For the first prototype, use one explicitly selected observation stream; do not mix single-sensor and fused-observation contracts implicitly.

## 4. Input Contract

One update represents one frame and contains frame metadata plus zero or more detections.

### Frame input

| Field | Type | Meaning |
|---|---|---|
| `frame_id` | Integer or string | Source-frame identifier |
| `timestamp` | Number | Capture time in a documented time base |
| `image_width` | Integer | Frame width in pixels |
| `image_height` | Integer | Frame height in pixels |
| `detections` | List | Normalized detections for this frame; may be empty |

### Detection record

| Field | Type | Required | Meaning |
|---|---|---|---|
| `detection_id` | String or integer | Recommended | Identifier unique within the frame |
| `class_id` or `class_name` | Integer or string | Yes | Class reported by P1 |
| `confidence` | Float | Yes | Detector confidence |
| `bbox_xyxy` | Four numbers | Yes | `[x1, y1, x2, y2]` in source-image pixels |
| `source` | String | Recommended | Detector/observation source |
| `quality` | Object or enum | Optional | P1 quality flags |

Contract rules:
- Use `[x1, y1, x2, y2]` consistently.
- Boxes and image dimensions must refer to the same image coordinate system.
- Timestamps must use a documented time base.
- An empty detection list is valid.
- Detector confidence is distinct from track state or track confidence.
- P1 remains the source of detection class and measured bounding box.

Illustrative input:

```json
{
  "frame_id": 125,
  "timestamp": 12.5,
  "image_width": 1280,
  "image_height": 720,
  "detections": [
    {
      "detection_id": "125-0",
      "class_name": "vehicle",
      "confidence": 0.91,
      "bbox_xyxy": [420, 180, 650, 360],
      "source": "perception"
    }
  ]
}
```

Example values are illustrative only.

## 5. Output Contract

P2 returns frame metadata and zero or more track records.

| Field | Type | Meaning |
|---|---|---|
| `track_id` | String or integer | Identifier unique within this tracker session |
| `frame_id` | Integer or string | Frame associated with output |
| `timestamp` | Number | Timestamp associated with update |
| `class_id` or `class_name` | Integer or string | Class inherited from observations |
| `bbox_xyxy` | Four numbers | Current image-space box |
| `state` | Enum | `tentative`, `confirmed`, `temporarily_missing`, `ended` |
| `last_detection_id` | String/integer/null | Latest associated detection, if any |
| `last_observed_timestamp` | Number | Latest matched observation time |
| `age_frames` | Integer | Frames since track creation |
| `hits` | Integer | Number of matched observations |
| `quality` | Object or enum | Optional diagnostics |

A track ID is session-scoped and does not establish real-world identity across separate sessions. Predicted or temporarily missing tracks must be explicitly labelled; they must not be presented as current detections.

Illustrative output:

```json
{
  "frame_id": 125,
  "timestamp": 12.5,
  "tracks": [
    {
      "track_id": 7,
      "frame_id": 125,
      "timestamp": 12.5,
      "class_name": "vehicle",
      "bbox_xyxy": [422, 181, 649, 359],
      "state": "confirmed",
      "last_detection_id": "125-0",
      "last_observed_timestamp": 12.5,
      "age_frames": 18,
      "hits": 16
    }
  ]
}
```

Example values are illustrative only.

## 6. Track Lifecycle

- **Tentative:** recently created and not yet sufficiently supported.
- **Confirmed:** supported by the configured evidence policy.
- **Temporarily missing:** no current detection was associated, but the track has not expired.
- **Ended:** no longer maintained as an active track.

Lifecycle thresholds belong in configuration, not in downstream consumers.

## 7. Suggested File Structure

```text
tracking_layer/
├── __init__.py
├── tracker_interface.py
├── track_models.py
├── tracking_manager.py
├── track_lifecycle.py
├── config.py
└── README.md
```

- `tracker_interface.py`: common API for a tracker backend.
- `track_models.py`: frame, detection, and track data structures.
- `tracking_manager.py`: accepts one frame update, invokes the backend, and normalizes output.
- `track_lifecycle.py`: state names and lifecycle transition definitions; no detection or depth algorithms.
- `config.py`: backend selection and lifecycle settings.
- `README.md`: usage and integration contract.

Do not copy detector adapters, video-source code, depth estimation, fusion logic, or world-model persistence into this directory.

## 8. Backend Selection

The project's research document names BoT-SORT as an initial candidate, with ByteTrack and OC-SORT as alternatives. Keep the backend behind `tracker_interface.py` so the implementation can be changed without altering P1 or downstream contracts. Selection should consider dataset evaluation, dependency compatibility, licensing, compute limits, and interface support.

## 9. Integration with P1

```text
P1 pipeline
  └── FrameDetections
          |
          v
P2 tracking_manager.update(frame_detections)
          |
          v
       TrackFrame
```

P2 must consume normalized detections, not import or call individual P1 model adapters.

## 10. Development Tasks

1. Freeze whether P2 receives P1 detections or post-fusion observations.
2. Define frame, detection, and track data models.
3. Define a backend-independent tracker interface.
4. Add a manager to normalize backend outputs.
5. Define lifecycle states and their output semantics.
6. Integrate with a generic recorded-video perception pipeline.
7. Document configuration and module boundaries.

## 11. Development Completion Criteria

P2's development scope is implemented when:
- Input/output schemas are defined.
- A backend is callable through a common interface.
- Track records contain session-scoped IDs and explicit lifecycle states.
- Empty-detection frames are supported.
- Outputs are independent of detector-specific classes.
- The module does not implement depth, VIO, sensor fusion, semantic scene interpretation, world-model persistence, or flight-control logic.

Runtime validation and quantitative performance evaluation are separate tasks.

## 12. References

Shield AI's public Vision Systems page describes EO/IR computer-vision capabilities for detection, tracking, and situational awareness. It is a capability-level reference, not a specification of proprietary internals: https://shield.ai/vision-systems/

BoT-SORT is a published multi-object tracking approach that combines motion and appearance information. Project research identifies it as an initial candidate, with ByteTrack and OC-SORT as alternatives:
- https://arxiv.org/abs/2206.14651
- https://github.com/NirAharon/BoT-SORT

---

**Architecture rule:** P1 detects objects; P2 maintains frame-to-frame track records; Depth/3D estimates spatial state; Multi-Modal Fusion combines sensor evidence; the ISR World Model maintains persistent scene context.