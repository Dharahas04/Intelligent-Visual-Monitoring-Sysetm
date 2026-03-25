import argparse
import json
import os
import warnings

import cv2
import numpy as np

warnings.filterwarnings("ignore", category=FutureWarning)


def parse_args():
    parser = argparse.ArgumentParser(description="ANPR video inference connector")
    parser.add_argument("--weights", required=True, help="Path to model weights")
    parser.add_argument("--source", required=True, help="Path to input video")
    parser.add_argument("--output", required=True, help="Path to output video")
    parser.add_argument("--conf", type=float, default=0.10, help="Confidence threshold")
    return parser.parse_args()


def validate_video(cap: cv2.VideoCapture, source: str) -> tuple[int, int, float, int]:
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open video: {source}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 20.0)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    if width <= 0 or height <= 0:
        raise RuntimeError("Invalid input video resolution.")
    if fps <= 0:
        fps = 20.0
    if frame_count > 0 and frame_count < 2:
        raise RuntimeError("Video too short: need at least 2 frames for stable analysis.")

    return width, height, fps, frame_count


def extract_detection_count(result) -> int:
    boxes = getattr(result, "boxes", None)
    if boxes is None:
        return 0
    try:
        return int(len(boxes))
    except Exception:
        return 0


def heuristic_plate_candidates(frame: np.ndarray) -> tuple[np.ndarray, int]:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.bilateralFilter(gray, 11, 17, 17)
    edges = cv2.Canny(blur, 30, 200)

    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:30]

    output = frame.copy()
    detections = 0
    frame_h, frame_w = frame.shape[:2]
    min_area = max(500, int(0.0008 * frame_h * frame_w))

    for contour in contours:
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.018 * perimeter, True)
        if len(approx) != 4:
            continue

        x, y, w, h = cv2.boundingRect(approx)
        area = w * h
        ratio = w / float(max(h, 1))

        if area < min_area:
            continue
        if ratio < 2.0 or ratio > 6.5:
            continue

        detections += 1
        cv2.rectangle(output, (x, y), (x + w, y + h), (0, 255, 255), 2)
        cv2.putText(
            output,
            "Plate Candidate",
            (x, max(20, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 255),
            2,
        )

    return output, detections


def create_video_writer(path: str, fps: float, width: int, height: int) -> tuple[cv2.VideoWriter, str]:
    codec_priority = ("avc1", "H264", "X264", "mp4v")
    for codec in codec_priority:
        writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*codec), fps, (width, height))
        if writer.isOpened():
            return writer, codec
        writer.release()
    raise RuntimeError(f"Unable to initialize output writer with supported codecs: {path}")


def compact_error_message(message: str, limit: int = 220) -> str:
    text = " ".join(str(message).split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def prepare_runtime_paths(output_dir: str) -> None:
    runtime_root = os.path.join(output_dir, ".runtime")
    cache_dir = os.path.join(runtime_root, "cache")
    mpl_dir = os.path.join(runtime_root, "mpl")
    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(mpl_dir, exist_ok=True)

    # Keep runtime caches inside project storage to avoid permission issues.
    os.environ.setdefault("XDG_CACHE_HOME", cache_dir)
    os.environ.setdefault("MPLCONFIGDIR", mpl_dir)

    home_dir = os.path.expanduser("~")
    if not os.access(home_dir, os.W_OK):
        os.environ["HOME"] = runtime_root


def load_yolov5_model(weights_path: str):
    try:
        import torch

        original_torch_load = torch.load

        def torch_load_compat(*args, **kwargs):
            # PyTorch >=2.6 defaults weights_only=True and breaks legacy YOLOv5 checkpoints.
            kwargs.setdefault("weights_only", False)
            return original_torch_load(*args, **kwargs)

        torch.load = torch_load_compat

        import yolov5
        warnings.filterwarnings(
            "ignore",
            message="`torch.cuda.amp.autocast",
            category=FutureWarning,
        )

        model = yolov5.load(weights_path, device="cpu", autoshape=True, verbose=False)
        return model, None
    except Exception as exc:
        return None, compact_error_message(exc)


def load_ultralytics_model(weights_path: str):
    try:
        from ultralytics import YOLO

        return YOLO(weights_path), None
    except Exception as exc:
        return None, compact_error_message(exc)


def main():
    args = parse_args()

    if not os.path.exists(args.weights):
        raise FileNotFoundError(f"Weights file not found: {args.weights}")
    if not os.path.exists(args.source):
        raise FileNotFoundError(f"Source file not found: {args.source}")
    if os.path.getsize(args.source) <= 1024:
        raise RuntimeError("Input video file appears corrupt or empty.")

    output_dir = os.path.dirname(os.path.abspath(args.output))
    os.makedirs(output_dir, exist_ok=True)
    prepare_runtime_paths(output_dir)

    ultralytics_model = None
    yolov5_model = None
    inference_mode = "HEURISTIC"
    model_warning = None

    ultralytics_model, yolo8_error = load_ultralytics_model(args.weights)
    if ultralytics_model is not None:
        inference_mode = "YOLOV8"
    else:
        yolov5_model, yolo5_error = load_yolov5_model(args.weights)
        if yolov5_model is not None:
            inference_mode = "YOLOV5"
            if hasattr(yolov5_model, "conf"):
                yolov5_model.conf = args.conf
            if hasattr(yolov5_model, "iou"):
                yolov5_model.iou = 0.45
        else:
            model_warning = (
                "Legacy checkpoint incompatible with available model runtimes. "
                "Running classical plate-candidate mode. "
                f"YOLOv8: {yolo8_error}. YOLOv5: {yolo5_error}"
            )

    cap = cv2.VideoCapture(args.source)
    frame_width, frame_height, fps, _ = validate_video(cap, args.source)

    writer, output_codec = create_video_writer(args.output, fps, frame_width, frame_height)

    processed_frames = 0
    total_detections = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        if frame is None or frame.size == 0:
            continue

        if inference_mode == "YOLOV8" and ultralytics_model is not None:
            try:
                results = ultralytics_model(frame, conf=args.conf, verbose=False)
                if results:
                    result = results[0]
                    total_detections += extract_detection_count(result)
                    rendered = result.plot()
                else:
                    rendered = frame
                writer.write(rendered)
                processed_frames += 1
                continue
            except Exception:
                yolov5_model, yolo5_error = load_yolov5_model(args.weights)
                if yolov5_model is not None:
                    inference_mode = "YOLOV5"
                else:
                    inference_mode = "HEURISTIC"
                    model_warning = (
                        "Model inference switched to classical plate-candidate mode due to runtime incompatibility. "
                        f"Reason: {yolo5_error}"
                    )

        if inference_mode == "YOLOV5" and yolov5_model is not None:
            try:
                yolo5_results = yolov5_model(frame, size=640)
                yolo5_detections = len(yolo5_results.xyxy[0]) if hasattr(yolo5_results, "xyxy") else 0
                total_detections += int(yolo5_detections)
                rendered = yolo5_results.render()[0]
                writer.write(rendered)
                processed_frames += 1
                continue
            except Exception as exc:
                inference_mode = "HEURISTIC"
                model_warning = (
                    "YOLOv5 inference error; switched to classical plate-candidate mode. "
                    f"Reason: {compact_error_message(exc)}"
                )

        rendered, detections = heuristic_plate_candidates(frame)
        total_detections += detections
        writer.write(rendered)
        processed_frames += 1

    cap.release()
    writer.release()

    if processed_frames == 0:
        raise RuntimeError("No frames were processed from input video.")
    if not os.path.exists(args.output) or os.path.getsize(args.output) <= 0:
        raise RuntimeError("Output video was not generated.")

    summary = {
        "service": "ANPR",
        "status": "COMPLETED",
        "mode": inference_mode,
        "warning": model_warning,
        "processedFrames": processed_frames,
        "totalDetections": total_detections,
        "videoCodec": output_codec,
        "output": os.path.abspath(args.output),
    }
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
