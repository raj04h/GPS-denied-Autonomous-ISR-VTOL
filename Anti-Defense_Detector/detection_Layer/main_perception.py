
from pathlib import Path
import sys

DETECTION_LAYER_DIR = Path(__file__).resolve().parent
DETECTOR_PROJECT_DIR = DETECTION_LAYER_DIR.parent
WORKSPACE_ROOT = DETECTOR_PROJECT_DIR.parent

if str(DETECTION_LAYER_DIR) not in sys.path:
    sys.path.insert(0, str(DETECTION_LAYER_DIR))

from detection_manager import DetectionManager
from detection_fusion import DetectionFusion

from Model_adaptor.rfdetr_adaptor import RFDETRDetector
from Model_adaptor.vehicle_adaptor import VEHICLEDETECTOR
from Model_adaptor.gun_adaptor import GUNDETECTOR
from Model_adaptor.weapon_adaptor import WEAPONDETECTOR

from eo_processing.eo_perception_pipeline import EOPerceptionPipeline


# Input configuration
INPUT_MODE = "video"  # video, camera, rtsp

VIDEO_PATH = (  # just remove this
    DETECTOR_PROJECT_DIR
    / "asset"
    / "drone_testing.mp4"
)
CAMERA_INDEX = 0
RTSP_URL = "rtsp://<camera-address>/<stream-path>"

# Output configuration
DISPLAY = True
SAVE_OUTPUT_VIDEO = True
MAX_FRAMES = None

OUTPUT_DIR = DETECTOR_PROJECT_DIR / "output"
OUTPUT_VIDEO = OUTPUT_DIR / "eo_perception_v1_result.mp4"
OUTPUT_LOG = OUTPUT_DIR / "eo_perception_v1.jsonl"

# Model weights
VEHICLE_WEIGHTS = WORKSPACE_ROOT / "models" / "vehicle_model.pt"
GUN_WEIGHTS = WORKSPACE_ROOT / "models" / "gun_model.pt"
WEAPON_WEIGHTS = WORKSPACE_ROOT / "models" / "weapon_model.pt"


def validate_configuration() -> None:
    if INPUT_MODE not in {"video", "camera", "rtsp"}:
        raise ValueError(
            "INPUT_MODE must be 'video', 'camera', or 'rtsp'."
        )

    model_paths = {
        "Vehicle model": VEHICLE_WEIGHTS,
        "Gun model": GUN_WEIGHTS,
        "Weapon model": WEAPON_WEIGHTS,
    }

    missing = [
        f"{name}: {path}"
        for name, path in model_paths.items()
        if not path.is_file()
    ]

    if INPUT_MODE == "video" and not VIDEO_PATH.is_file():
        missing.append(f"Input video: {VIDEO_PATH}")

    if INPUT_MODE == "rtsp" and (
        not RTSP_URL
        or "<camera-address>" in RTSP_URL
        or "<stream-path>" in RTSP_URL
    ):
        raise ValueError(
            "Configure RTSP_URL with the actual stream address."
        )

    if missing:
        raise FileNotFoundError(
            "Required files are missing:\n" + "\n".join(missing)
        )


def build_detection_manager() -> DetectionManager:
    print("Initializing EO/RGB detectors...")

    detectors = {
        "RF-DETR": RFDETRDetector(
            confidence_threshold=0.40,
        ),
        "YOLOv8m_Defence": VEHICLEDETECTOR(
            weights_path=str(VEHICLE_WEIGHTS),
            confidence_threshold=0.50,
        ),
        "gun_dtct": GUNDETECTOR(
            weights_path=str(GUN_WEIGHTS),
            confidence_threshold=0.50,
        ),
        "YOLO26x_Weapon": WEAPONDETECTOR(
            weights_path=str(WEAPON_WEIGHTS),
            confidence_threshold=0.50,
        ),
    }

    fusion = DetectionFusion(
        iou_threshold=0.50,
        confidence_threshold=0.25,
    )

    manager = DetectionManager(
        detectors=detectors,
        fusion=fusion,
    )

    print("Configured detectors:")
    for name in manager.get_detector_names():
        print(f"  - {name}")

    return manager


def get_input_configuration() -> dict:
    if INPUT_MODE == "video":
        return {
            "video_path": str(VIDEO_PATH),
            "source_type": "video",
        }

    if INPUT_MODE == "camera":
        return {
            "video_path": CAMERA_INDEX,
            "source_type": "camera",
            "camera_index": CAMERA_INDEX,
        }

    return {
        "video_path": RTSP_URL,
        "source_type": "rtsp",
        "rtsp_url": RTSget_input_configurationget_input_configurationP_URL,
    }


def main() -> None:
    print("\nEO RGB PERCEPTION V1")
    print(f"Input mode: {INPUT_MODE}")
    print(f"Live display: {'enabled' if DISPLAY else 'disabled'}")

    validate_configuration()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    manager = build_detection_manager()

    pipeline_options = {
        **get_input_configuration(),
        "detection_manager": manager,
        "output_video_path": (
            str(OUTPUT_VIDEO) if SAVE_OUTPUT_VIDEO else None
        ),
        "output_log_path": str(OUTPUT_LOG),
        "max_frames": MAX_FRAMES,
        "display": DISPLAY,
    }

    pipeline = EOPerceptionPipeline(**pipeline_options)

    print("\nStarting perception pipeline.")
    print("Press Q in the display window to stop, if supported.")
    print("Press Ctrl+C in the terminal to interrupt.")

    try:
        summary = pipeline.run()
    except KeyboardInterrupt:
        print("\nStop requested by user.")
        return

    if not isinstance(summary, dict):
        print("Pipeline finished without a summary dictionary.")
        return

    frames_processed = summary.get("processed_frames", 0)
    frames_failed = summary.get("failed_frames", 0)
    total_time_s = summary.get("wall_time_sec", 0.0)
    average_fps = summary.get("effective_fps", 0.0)
    average_inference_ms = summary.get("average_inference_ms", 0.0)

    print("\nEO PERCEPTION SUMMARY")
    print(f"Frames processed        : {frames_processed}")
    print(f"Frames failed           : {frames_failed}")
    print(f"Total runtime           : {total_time_s:.2f} s")
    print(f"Effective processing FPS: {average_fps:.2f}")
    print(f"Average inference       : {average_inference_ms:.2f} ms")

    if SAVE_OUTPUT_VIDEO:
        print(f"Output video: {OUTPUT_VIDEO}")
    print(f"Detection log: {OUTPUT_LOG}")


if __name__ == "__main__":
    main()
