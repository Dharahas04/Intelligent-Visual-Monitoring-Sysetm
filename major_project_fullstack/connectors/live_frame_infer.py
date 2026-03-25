import argparse
import base64
import json

import cv2
import numpy as np

_HOG = cv2.HOGDescriptor()
_HOG.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())


def parse_args():
    parser = argparse.ArgumentParser(description="Live frame inference bridge")
    parser.add_argument("--service", required=True, help="ANPR | MASK_DETECTION | CROWD_GATHERING")
    return parser.parse_args()


def decode_frame(frame_payload: str):
    payload = (frame_payload or "").strip()
    if not payload:
        raise RuntimeError("Empty frame payload")
    if payload.startswith("data:image") and "," in payload:
        payload = payload.split(",", 1)[1]
    raw = base64.b64decode(payload)
    if not raw:
        raise RuntimeError("Unable to decode base64 frame")
    frame = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise RuntimeError("Invalid image buffer")
    return frame


def clamp(value, low=0.0, high=99.0):
    return float(max(low, min(high, value)))


def heuristic_anpr(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.bilateralFilter(gray, 11, 17, 17)
    edges = cv2.Canny(blur, 30, 200)

    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:40]

    h, w = frame.shape[:2]
    min_area = max(500, int(0.0008 * h * w))
    boxes = []

    for contour in contours:
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.018 * perimeter, True)
        if len(approx) != 4:
            continue
        x, y, bw, bh = cv2.boundingRect(approx)
        area = bw * bh
        ratio = bw / float(max(1, bh))
        if area < min_area:
            continue
        if ratio < 2.0 or ratio > 6.6:
            continue
        boxes.append({"x": int(x), "y": int(y), "w": int(bw), "h": int(bh)})
        if len(boxes) >= 10:
            break

    detections = len(boxes)
    confidence = clamp(32 + detections * 9)
    return {
        "service": "ANPR",
        "status": "COMPLETED",
        "detections": detections,
        "alert": detections > 0,
        "confidencePct": round(confidence, 2),
        "boxes": boxes,
        "message": "Plate candidates detected" if detections > 0 else "No strong plate candidates"
    }


def heuristic_mask(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=5, minSize=(28, 28))

    boxes = []
    mask_count = 0
    no_mask_count = 0

    for (x, y, w, h) in faces[:12]:
        x = int(x)
        y = int(y)
        w = int(w)
        h = int(h)
        x2 = min(frame.shape[1] - 1, x + w)
        y2 = min(frame.shape[0] - 1, y + h)
        face = frame[y:y2, x:x2]
        label, confidence_pct = estimate_mask_label(face)
        if label == "MASK":
            mask_count += 1
        else:
            no_mask_count += 1
        boxes.append({
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "label": label,
            "confidencePct": confidence_pct
        })

    detected_faces = len(boxes)
    confidence = max([b["confidencePct"] for b in boxes], default=0.0)
    return {
        "service": "MASK_DETECTION",
        "status": "COMPLETED",
        "detections": detected_faces,
        "maskDetections": mask_count,
        "noMaskDetections": no_mask_count,
        "alert": no_mask_count > 0,
        "confidencePct": round(confidence, 2),
        "boxes": boxes,
        "message": "No-mask person detected" if no_mask_count > 0 else "Mask compliant"
    }


def heuristic_crowd(frame):
    rects, _ = _HOG.detectMultiScale(frame, winStride=(6, 6), padding=(8, 8), scale=1.05)
    boxes = [{"x": int(x), "y": int(y), "w": int(w), "h": int(h)} for (x, y, w, h) in rects[:20]]
    people = len(boxes)
    gather_alert = people >= 5
    confidence = clamp(25 + people * 6.5)
    return {
        "service": "CROWD_GATHERING",
        "status": "COMPLETED",
        "detections": people,
        "gatherAlert": gather_alert,
        "alert": gather_alert,
        "confidencePct": round(confidence, 2),
        "boxes": boxes,
        "message": "Crowd density high" if gather_alert else "Crowd density normal"
    }


def estimate_mask_label(face_bgr: np.ndarray):
    h, w = face_bgr.shape[:2]
    if h < 12 or w < 12:
        return "NO_MASK", 20.0

    lower_half = face_bgr[h // 2 :, :]
    ycrcb = cv2.cvtColor(lower_half, cv2.COLOR_BGR2YCrCb)
    skin = cv2.inRange(ycrcb, (0, 133, 77), (255, 173, 127))
    skin_ratio = float(cv2.countNonZero(skin)) / float(lower_half.shape[0] * lower_half.shape[1] + 1e-6)

    hsv = cv2.cvtColor(lower_half, cv2.COLOR_BGR2HSV)
    saturation = float(np.mean(hsv[:, :, 1])) / 255.0

    mask_score = (1.0 - min(1.0, skin_ratio * 2.2)) * 0.7 + (1.0 - saturation) * 0.3
    mask_score = float(np.clip(mask_score, 0.0, 1.0))

    if mask_score >= 0.55:
        return "MASK", clamp(mask_score * 100.0)
    return "NO_MASK", clamp((1.0 - mask_score) * 100.0)


def main():
    args = parse_args()
    frame_payload = input()
    frame = decode_frame(frame_payload)

    service = (args.service or "").strip().upper()
    if service == "ANPR":
        result = heuristic_anpr(frame)
    elif service == "MASK_DETECTION":
        result = heuristic_mask(frame)
    elif service in {"CROWD_GATHERING", "CROWD", "CROWD_DETECTION"}:
        result = heuristic_crowd(frame)
    else:
        raise RuntimeError(f"Unsupported live service: {args.service}")

    result["frameWidth"] = int(frame.shape[1])
    result["frameHeight"] = int(frame.shape[0])

    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({
            "status": "FAILED",
            "error": str(exc)
        }))
