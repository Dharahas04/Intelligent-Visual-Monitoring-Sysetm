import argparse
import json
import os
from pathlib import Path

import cv2
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(description="Mask detection connector (lightweight runtime)")
    parser.add_argument("--video", required=True, help="Input video path")
    parser.add_argument("--output", required=True, help="Output video path")
    parser.add_argument("--face-threshold", type=float, default=1.1, help="Haar cascade scale factor")
    return parser.parse_args()


def create_writer(path: str, fps: float, width: int, height: int):
    codec_priority = ("avc1", "H264", "X264", "mp4v")
    for codec in codec_priority:
        writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*codec), fps, (width, height))
        if writer.isOpened():
            return writer, codec
        writer.release()
    raise RuntimeError(f"Unable to initialize output writer: {path}")


def estimate_mask_confidence(face_bgr: np.ndarray) -> tuple[str, float]:
    h, w = face_bgr.shape[:2]
    if h < 10 or w < 10:
        return "UNKNOWN", 0.0

    lower_half = face_bgr[h // 2 :, :]
    ycrcb = cv2.cvtColor(lower_half, cv2.COLOR_BGR2YCrCb)
    skin = cv2.inRange(ycrcb, (0, 133, 77), (255, 173, 127))
    skin_ratio = float(cv2.countNonZero(skin)) / float(lower_half.shape[0] * lower_half.shape[1] + 1e-6)

    hsv = cv2.cvtColor(lower_half, cv2.COLOR_BGR2HSV)
    saturation = float(np.mean(hsv[:, :, 1])) / 255.0

    # Lower visible skin ratio and lower saturation generally indicate mask coverage.
    score = (1.0 - min(1.0, skin_ratio * 2.2)) * 0.7 + (1.0 - saturation) * 0.3
    score = float(np.clip(score, 0.0, 1.0))

    if score >= 0.55:
        return "MASK", score
    return "NO_MASK", 1.0 - score


def main():
    args = parse_args()

    if not os.path.exists(args.video):
        raise FileNotFoundError(f"Input video not found: {args.video}")
    if os.path.getsize(args.video) <= 1024:
        raise RuntimeError("Input video is too small/corrupt.")

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open input video: {args.video}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 20.0)
    if width <= 0 or height <= 0:
        raise RuntimeError("Invalid input video resolution.")

    writer, codec = create_writer(str(output_path), fps, width, height)

    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    if not os.path.exists(cascade_path):
        raise RuntimeError("OpenCV Haar cascade not found in runtime.")
    face_cascade = cv2.CascadeClassifier(cascade_path)
    if face_cascade.empty():
        raise RuntimeError("Unable to initialize face detector.")

    processed_frames = 0
    total_faces = 0
    mask_count = 0
    no_mask_count = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame is None or frame.size == 0:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=max(1.01, args.face_threshold),
            minNeighbors=5,
            minSize=(30, 30),
        )

        for x, y, w, h in faces:
            x = max(0, x)
            y = max(0, y)
            x2 = min(width - 1, x + w)
            y2 = min(height - 1, y + h)
            face = frame[y:y2, x:x2]
            if face.size == 0:
                continue

            label, confidence = estimate_mask_confidence(face)
            if label == "MASK":
                mask_count += 1
                color = (0, 220, 120)
                text = f"Mask {confidence * 100:.1f}%"
            elif label == "NO_MASK":
                no_mask_count += 1
                color = (0, 0, 255)
                text = f"No Mask {confidence * 100:.1f}%"
            else:
                color = (200, 200, 200)
                text = "Unknown"

            total_faces += 1
            cv2.rectangle(frame, (x, y), (x2, y2), color, 2)
            cv2.putText(frame, text, (x, max(18, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

        cv2.putText(
            frame,
            f"Faces: {len(faces)}  Mask: {mask_count}  NoMask: {no_mask_count}",
            (12, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
        )

        writer.write(frame)
        processed_frames += 1

    cap.release()
    writer.release()

    if processed_frames == 0:
        raise RuntimeError("No frames were processed from input video.")
    if not output_path.exists() or output_path.stat().st_size <= 0:
        raise RuntimeError("Output video was not generated.")

    print(
        json.dumps(
            {
                "service": "MASK_DETECTION",
                "status": "COMPLETED",
                "processedFrames": processed_frames,
                "totalFaces": total_faces,
                "maskDetections": mask_count,
                "noMaskDetections": no_mask_count,
                "videoCodec": codec,
                "output": str(output_path),
            }
        )
    )


if __name__ == "__main__":
    main()
