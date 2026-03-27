import argparse
import json
import math
import os
from pathlib import Path

import cv2
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(description="Crowd gathering connector")
    parser.add_argument("--video", required=True, help="Input video path")
    parser.add_argument("--output", required=True, help="Output video path")
    parser.add_argument("--line-y", type=int, default=-1, help="Line-crossing Y coordinate")
    parser.add_argument("--gather-distance", type=float, default=95.0, help="Distance threshold for gathering pairs")
    parser.add_argument("--conf-threshold", type=float, default=0.30, help="Person confidence threshold")
    parser.add_argument("--track-distance", type=float, default=80.0, help="Max centroid distance for track match")
    parser.add_argument("--max-missed", type=int, default=10, help="Frames to keep unmatched track alive")
    parser.add_argument("--yolo-model", default="", help="Optional YOLO model path")
    return parser.parse_args()


def create_writer(path: str, fps: float, width: int, height: int):
    codec_priority = ("avc1", "H264", "X264", "mp4v")
    for codec in codec_priority:
        writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*codec), fps, (width, height))
        if writer.isOpened():
            return writer, codec
        writer.release()
    raise RuntimeError(f"Unable to initialize output writer: {path}")


def prepare_runtime_paths(output_dir: str) -> None:
    runtime_root = os.path.join(output_dir, ".runtime")
    cache_dir = os.path.join(runtime_root, "cache")
    mpl_dir = os.path.join(runtime_root, "mpl")
    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(mpl_dir, exist_ok=True)
    os.environ.setdefault("XDG_CACHE_HOME", cache_dir)
    os.environ.setdefault("MPLCONFIGDIR", mpl_dir)
    home_dir = os.path.expanduser("~")
    if not os.access(home_dir, os.W_OK):
        os.environ["HOME"] = runtime_root


def detect_people_hog(hog: cv2.HOGDescriptor, frame: np.ndarray):
    boxes, scores = hog.detectMultiScale(
        frame,
        winStride=(8, 8),
        padding=(8, 8),
        scale=1.03,
    )

    if len(boxes) == 0:
        return []

    rects = []
    confidences = []
    for (x, y, w, h), score in zip(boxes, scores):
        rects.append([int(x), int(y), int(w), int(h)])
        confidences.append(float(score))

    keep = cv2.dnn.NMSBoxes(rects, confidences, score_threshold=0.2, nms_threshold=0.45)
    if keep is None or len(keep) == 0:
        return []

    detections = []
    for idx in np.array(keep).reshape(-1):
        x, y, w, h = rects[int(idx)]
        x1, y1, x2, y2 = x, y, x + w, y + h
        detections.append((x1, y1, x2, y2, confidences[int(idx)]))
    return detections


def default_yolo_model_path(explicit_path: str) -> Path:
    if explicit_path:
        return Path(explicit_path).expanduser().resolve()
    workspace_root = Path(__file__).resolve().parents[2]
    return workspace_root / "Crowd-Gathering-Detection-main" / "yolov8s.pt"


def try_load_yolo(model_path: Path):
    if not model_path.exists():
        return None, "HOG", f"YOLO model not found: {model_path}"
    try:
        from ultralytics import YOLO

        model = YOLO(str(model_path))
        return model, "YOLOV8", ""
    except Exception as exc:
        return None, "HOG", f"YOLO unavailable, fallback to HOG: {exc}"


def detect_people_yolo(model, frame: np.ndarray, conf_threshold: float):
    results = model(frame, verbose=False, conf=conf_threshold, classes=[0])
    if not results:
        return []

    detections = []
    h, w = frame.shape[:2]
    boxes = results[0].boxes
    if boxes is None:
        return detections

    xyxy = boxes.xyxy.cpu().numpy() if hasattr(boxes.xyxy, "cpu") else np.array(boxes.xyxy)
    confs = boxes.conf.cpu().numpy() if hasattr(boxes.conf, "cpu") else np.array(boxes.conf)
    classes = boxes.cls.cpu().numpy() if hasattr(boxes.cls, "cpu") else np.array(boxes.cls)

    for coords, conf, cls in zip(xyxy, confs, classes):
        if int(cls) != 0:
            continue
        if float(conf) < conf_threshold:
            continue
        x1, y1, x2, y2 = map(int, coords[:4])
        x1 = max(0, min(x1, w - 1))
        y1 = max(0, min(y1, h - 1))
        x2 = max(0, min(x2, w - 1))
        y2 = max(0, min(y2, h - 1))
        if x2 <= x1 or y2 <= y1:
            continue
        detections.append((x1, y1, x2, y2, float(conf)))
    return detections


def gathering_pairs(centers: list[tuple[int, int]], threshold: float):
    pairs = []
    threshold_sq = threshold * threshold
    for i in range(len(centers)):
        for j in range(i + 1, len(centers)):
            dx = centers[i][0] - centers[j][0]
            dy = centers[i][1] - centers[j][1]
            if (dx * dx + dy * dy) <= threshold_sq:
                pairs.append((centers[i], centers[j]))
    return pairs


def update_tracks(tracks: dict[int, dict], centers: list[tuple[int, int]], next_track_id: int, max_distance: float, max_missed: int):
    for track in tracks.values():
        track["updated"] = False

    unmatched_indices = set(range(len(centers)))
    used_track_ids = set()

    for idx, center in enumerate(centers):
        best_track_id = None
        best_distance = max_distance

        for track_id, track in tracks.items():
            if track_id in used_track_ids:
                continue
            px, py = track["centroid"]
            dist = math.hypot(center[0] - px, center[1] - py)
            if dist <= best_distance:
                best_distance = dist
                best_track_id = track_id

        if best_track_id is None:
            continue

        track = tracks[best_track_id]
        track["last_centroid"] = track["centroid"]
        track["centroid"] = center
        track["missed"] = 0
        track["updated"] = True
        used_track_ids.add(best_track_id)
        unmatched_indices.discard(idx)

    for idx in sorted(unmatched_indices):
        center = centers[idx]
        tracks[next_track_id] = {
            "centroid": center,
            "last_centroid": center,
            "missed": 0,
            "updated": True,
            "counted": False,
        }
        next_track_id += 1

    stale_ids = []
    for track_id, track in tracks.items():
        if not track["updated"]:
            track["missed"] += 1
        if track["missed"] > max_missed:
            stale_ids.append(track_id)
    for track_id in stale_ids:
        tracks.pop(track_id, None)

    return next_track_id


def main():
    args = parse_args()

    if not os.path.exists(args.video):
        raise FileNotFoundError(f"Input video not found: {args.video}")
    if os.path.getsize(args.video) <= 1024:
        raise RuntimeError("Input video is too small/corrupt.")

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prepare_runtime_paths(str(output_path.parent))

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open input video: {args.video}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 20.0)
    if width <= 0 or height <= 0:
        raise RuntimeError("Invalid input video resolution.")

    line_y = args.line_y if args.line_y >= 0 else int(height * 0.72)
    writer, codec = create_writer(str(output_path), fps, width, height)

    yolo_model, detector_mode, warning = try_load_yolo(default_yolo_model_path(args.yolo_model))
    hog = None
    if yolo_model is None:
        hog = cv2.HOGDescriptor()
        hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    processed_frames = 0
    line_cross_count = 0
    gather_event_frames = 0
    people_sum = 0
    peak_people = 0

    tracks: dict[int, dict] = {}
    next_track_id = 1

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame is None or frame.size == 0:
            continue

        if yolo_model is not None:
            people = detect_people_yolo(yolo_model, frame, args.conf_threshold)
        else:
            people = detect_people_hog(hog, frame)

        centers = [((x1 + x2) // 2, (y1 + y2) // 2) for x1, y1, x2, y2, _ in people]
        next_track_id = update_tracks(tracks, centers, next_track_id, args.track_distance, args.max_missed)

        for track in tracks.values():
            if not track["updated"]:
                continue
            prev_y = track["last_centroid"][1]
            curr_y = track["centroid"][1]
            crossed = (prev_y < line_y <= curr_y) or (prev_y > line_y >= curr_y)
            if crossed and not track["counted"]:
                line_cross_count += 1
                track["counted"] = True

        for x1, y1, x2, y2, score in people:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (56, 214, 120), 2)
            cv2.putText(
                frame,
                f"Person {score:.2f}",
                (x1, max(18, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (56, 214, 120),
                1,
            )

        pairs = gathering_pairs(centers, args.gather_distance)
        if pairs:
            gather_event_frames += 1
            for c1, c2 in pairs[:28]:
                cv2.line(frame, c1, c2, (0, 130, 255), 2)
                cv2.circle(frame, c1, 4, (0, 130, 255), -1)
                cv2.circle(frame, c2, 4, (0, 130, 255), -1)

        cv2.line(frame, (25, line_y), (max(30, width - 25), line_y), (255, 127, 0), 2)
        cv2.putText(frame, f"People: {len(people)}", (14, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 244, 0), 2)
        cv2.putText(frame, f"Line Cross: {line_cross_count}", (14, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 244, 0), 2)
        cv2.putText(frame, f"Gather Frames: {gather_event_frames}", (14, 84), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 130, 255), 2)
        cv2.putText(frame, f"Detector: {detector_mode}", (14, 112), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (220, 220, 220), 2)

        if frame.shape[1] != width or frame.shape[0] != height:
            frame = cv2.resize(frame, (width, height))
        writer.write(frame)

        processed_frames += 1
        people_sum += len(people)
        peak_people = max(peak_people, len(people))

    cap.release()
    writer.release()

    if processed_frames == 0:
        raise RuntimeError("No frames were processed from input video.")
    if not output_path.exists() or output_path.stat().st_size <= 0:
        raise RuntimeError("Output video was not generated.")

    avg_people = people_sum / processed_frames if processed_frames else 0.0
    print(
        json.dumps(
            {
                "service": "CROWD_GATHERING",
                "status": "COMPLETED",
                "processedFrames": processed_frames,
                "lineCrossCount": line_cross_count,
                "gatherEventFrames": gather_event_frames,
                "averagePeoplePerFrame": round(avg_people, 3),
                "peakPeople": peak_people,
                "detectorMode": detector_mode,
                "warning": warning,
                "videoCodec": codec,
                "output": str(output_path),
            }
        )
    )


if __name__ == "__main__":
    main()
