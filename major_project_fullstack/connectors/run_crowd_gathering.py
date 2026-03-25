import argparse
import json
import os
from pathlib import Path

import cv2
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(description="Crowd gathering connector (lightweight runtime)")
    parser.add_argument("--video", required=True, help="Input video path")
    parser.add_argument("--output", required=True, help="Output video path")
    parser.add_argument("--line-y", type=int, default=-1, help="Line-crossing Y coordinate")
    parser.add_argument("--gather-distance", type=float, default=90.0, help="Distance threshold for gathering pairs")
    return parser.parse_args()


def create_writer(path: str, fps: float, width: int, height: int):
    codec_priority = ("avc1", "H264", "X264", "mp4v")
    for codec in codec_priority:
        writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*codec), fps, (width, height))
        if writer.isOpened():
            return writer, codec
        writer.release()
    raise RuntimeError(f"Unable to initialize output writer: {path}")


def detect_people(hog: cv2.HOGDescriptor, frame: np.ndarray):
    boxes, scores = hog.detectMultiScale(
        frame,
        winStride=(8, 8),
        padding=(8, 8),
        scale=1.03,
    )
    people = []
    for (x, y, w, h), score in zip(boxes, scores):
        if float(score) < 0.2:
            continue
        people.append((int(x), int(y), int(x + w), int(y + h), float(score)))
    return people


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

    line_y = args.line_y if args.line_y >= 0 else int(height * 0.72)
    line_offset = 8
    writer, codec = create_writer(str(output_path), fps, width, height)

    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    processed_frames = 0
    line_cross_count = 0
    gather_event_frames = 0
    people_sum = 0
    peak_people = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame is None or frame.size == 0:
            continue

        people = detect_people(hog, frame)
        centers: list[tuple[int, int]] = []

        for x1, y1, x2, y2, score in people:
            centers.append(((x1 + x2) // 2, (y1 + y2) // 2))
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

        for cx, cy in centers:
            if abs(cy - line_y) <= line_offset:
                line_cross_count += 1

        pairs = gathering_pairs(centers, args.gather_distance)
        if pairs:
            gather_event_frames += 1
            for c1, c2 in pairs[:24]:
                cv2.line(frame, c1, c2, (0, 130, 255), 2)
                cv2.circle(frame, c1, 4, (0, 130, 255), -1)
                cv2.circle(frame, c2, 4, (0, 130, 255), -1)

        cv2.line(frame, (25, line_y), (max(30, width - 25), line_y), (255, 127, 0), 2)
        cv2.putText(frame, f"People: {len(people)}", (14, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 244, 0), 2)
        cv2.putText(
            frame,
            f"Line Cross: {line_cross_count}",
            (14, 56),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 244, 0),
            2,
        )
        cv2.putText(
            frame,
            f"Gather Frames: {gather_event_frames}",
            (14, 84),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 130, 255),
            2,
        )

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
                "videoCodec": codec,
                "output": str(output_path),
            }
        )
    )


if __name__ == "__main__":
    main()
