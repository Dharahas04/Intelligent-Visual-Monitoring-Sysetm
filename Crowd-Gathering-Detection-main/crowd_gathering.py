# from ultralytics import YOLO
# import cv2
# import numpy as np

# # Load the pre-trained YOLOv8 model
# model = YOLO("yolov8s.pt")  # Use yolov8s.pt or yolov8m.pt for better accuracy

# # Video path
# video_path = "/Users/saidharahasrao/Downloads/Crowd-Gathering-Detection-main/3.mp4"
# cap = cv2.VideoCapture(video_path)

# # Output video settings
# output_path = "crowd_gathering.mp4"
# frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
# frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
# fps = int(cap.get(cv2.CAP_PROP_FPS))
# fourcc = cv2.VideoWriter_fourcc(*'mp4v')
# out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))

# # Line position for counting
# count_line_position = 400
# offset = 6
# counter = 0

# # Function to detect gatherings
# def detect_gatherings(boxes, threshold=50):
#     centers = [(int((x1 + x2) / 2), int((y1 + y2) / 2)) for x1, y1, x2, y2 in boxes]
#     gatherings = []
#     for i, c1 in enumerate(centers):
#         for j, c2 in enumerate(centers):
#             if i != j:
#                 dist = np.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)
#                 if dist < threshold:
#                     gatherings.append((c1, c2))
#     return gatherings

# # Process video frames
# while cap.isOpened():
#     ret, frame = cap.read()
#     if not ret:
#         break

#     # Predict using YOLOv8
#     results = model(frame)

#     # Extract person detections
#     person_boxes = []
#     for box in results[0].boxes:
#         x1, y1, x2, y2 = map(int, box.xyxy[0])  # Coordinates
#         cls = int(box.cls[0])  # Class ID
#         if cls == 0:  # Class 0 corresponds to "person"
#             # Ensure bounding box stays within frame
#             x1 = max(0, min(x1, frame_width - 1))
#             y1 = max(0, min(y1, frame_height - 1))
#             x2 = max(0, min(x2, frame_width - 1))
#             y2 = max(0, min(y2, frame_height - 1))
#             person_boxes.append((x1, y1, x2, y2))
#             label = f"Person {box.conf[0]:.2f}"  # Confidence
#             # Adjust label position to stay in frame
#             label_y = max(15, y1 - 10)
#             cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
#             cv2.putText(frame, label, (x1, label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

#     # Counting logic
#     detect = []
#     for (x1, y1, x2, y2) in person_boxes:
#         cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
#         detect.append((cx, cy))
#         if cy < (count_line_position + offset) and cy > (count_line_position - offset):
#             counter += 1

#     # Draw counting line
#     line_y = max(0, min(count_line_position, frame_height - 1))
#     cv2.line(frame, (25, line_y), (frame_width - 25, line_y), (255, 127, 0), 3)
#     # Draw human count text at top-left with padding, always visible
#     text = f"Human Count (Cross Line): {counter}"
#     (text_width, text_height), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)
#     text_x = 10
#     text_y = 10 + text_height
#     if text_y + text_height > frame_height:
#         text_y = frame_height - text_height - 10
#     cv2.putText(frame, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 244, 0), 2)

#     # Detect gatherings
#     gatherings = detect_gatherings(person_boxes)
#     for g in gatherings:
#         c1, c2 = g
#         # Ensure circles and lines stay in frame
#         c1 = (max(0, min(c1[0], frame_width - 1)), max(0, min(c1[1], frame_height - 1)))
#         c2 = (max(0, min(c2[0], frame_width - 1)), max(0, min(c2[1], frame_height - 1)))
#         cv2.circle(frame, c1, 10, (0, 0, 255), -1)
#         cv2.circle(frame, c2, 10, (0, 0, 255), -1)
#         cv2.line(frame, c1, c2, (255, 0, 0), 2)
#         midpoint = ((c1[0] + c2[0]) // 2, (c1[1] + c2[1]) // 2)
#         midpoint = (max(0, min(midpoint[0], frame_width - 80)), max(15, min(midpoint[1], frame_height - 10)))
#         cv2.putText(frame, "Gathering!", midpoint, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

#     # Show total detections in the frame
#     cv2.putText(frame, f"Total People in Frame: {len(person_boxes)}", (50, min(90, frame_height - 20)), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 244, 0), 2)

#     # Display the frame
#     cv2.imshow("YOLOv8 Human Detection", frame)
#     out.write(frame)

#     # Exit on ESC key
#     if cv2.waitKey(1) == 27:
#         break

# # Release resources
# cap.release()
# out.release()
# cv2.destroyAllWindows()
# =====================================================
# SMART CROWD GATHERING DETECTION (FINAL VERSION)
# YOLOv8 + DBSCAN + TIME PERSISTENCE
# =====================================================

# from ultralytics import YOLO
# import cv2
# import numpy as np
# import time
# from sklearn.cluster import DBSCAN

# # =====================================================
# # CONFIG
# # =====================================================

# MODEL_PATH = "yolov8s.pt"      # auto downloads first time
# VIDEO_PATH = "3.mp4"          # use 0 for webcam
# OUTPUT_PATH = "crowd_output.mp4"

# RESIZE_W = 640
# RESIZE_H = 480

# COUNT_LINE_Y = 350
# LINE_OFFSET = 8

# # ---- Gathering parameters ----
# GATHER_EPS = int(RESIZE_W * 0.09)   # distance threshold (auto scaled)
# MIN_PEOPLE_GROUP = 3               # minimum people to form group
# GATHER_TIME_THRESHOLD = 40         # frames (~2 sec)

# # =====================================================
# # LOAD MODEL
# # =====================================================

# print("Loading YOLO model...")
# model = YOLO(MODEL_PATH)

# # =====================================================
# # VIDEO SETUP
# # =====================================================

# cap = cv2.VideoCapture(VIDEO_PATH)

# fps = int(cap.get(cv2.CAP_PROP_FPS)) or 25
# fourcc = cv2.VideoWriter_fourcc(*'mp4v')
# out = cv2.VideoWriter(OUTPUT_PATH, fourcc, fps, (RESIZE_W, RESIZE_H))

# # =====================================================
# # FUNCTIONS
# # =====================================================

# def detect_people(frame):
#     """Detect persons using YOLO"""
#     results = model(frame, verbose=False)

#     boxes = []
#     for box in results[0].boxes:
#         if int(box.cls[0]) == 0:  # person
#             x1, y1, x2, y2 = map(int, box.xyxy[0])
#             conf = float(box.conf[0])
#             boxes.append((x1, y1, x2, y2, conf))

#     return boxes


# def detect_gatherings(boxes):
#     """Cluster nearby people using DBSCAN"""
#     if len(boxes) < MIN_PEOPLE_GROUP:
#         return []

#     centers = np.array([
#         ((x1+x2)//2, (y1+y2)//2)
#         for x1, y1, x2, y2, _ in boxes
#     ])

#     clustering = DBSCAN(eps=GATHER_EPS,
#                         min_samples=MIN_PEOPLE_GROUP).fit(centers)

#     labels = clustering.labels_

#     groups = []
#     for label in set(labels):
#         if label == -1:
#             continue
#         groups.append(centers[labels == label])

#     return groups


# # =====================================================
# # MAIN LOOP
# # =====================================================

# counter = 0
# gather_timer = 0
# prev_time = time.time()

# print("Starting detection... Press ESC to quit")

# while cap.isOpened():

#     ret, frame = cap.read()
#     if not ret:
#         break

#     frame = cv2.resize(frame, (RESIZE_W, RESIZE_H))

#     # -------------------------------------
#     # Person detection
#     # -------------------------------------
#     person_boxes = detect_people(frame)

#     centers = []

#     for (x1, y1, x2, y2, conf) in person_boxes:

#         cx = (x1+x2)//2
#         cy = (y1+y2)//2
#         centers.append((cx, cy))

#         cv2.rectangle(frame, (x1,y1), (x2,y2), (0,255,0), 2)
#         cv2.putText(frame, f"{conf:.2f}", (x1,y1-5),
#                     cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0,255,0), 1)

#         # Line crossing
#         if abs(cy - COUNT_LINE_Y) < LINE_OFFSET:
#             counter += 1

#     # -------------------------------------
#     # Draw counting line
#     # -------------------------------------
#     cv2.line(frame, (20, COUNT_LINE_Y),
#              (RESIZE_W-20, COUNT_LINE_Y),
#              (255,127,0), 3)

#     # -------------------------------------
#     # Gathering detection
#     # -------------------------------------
#     groups = detect_gatherings(person_boxes)

#     # TIME FILTER (important)
#     if len(groups) > 0:
#         gather_timer += 1
#     else:
#         gather_timer = max(0, gather_timer - 2)

#     # Only alert if persistent
#     largest_group = max([len(g) for g in groups], default=0)

#     if gather_timer > GATHER_TIME_THRESHOLD and largest_group >= 4:

#         for group in groups:

#             for (cx, cy) in group:
#                 cv2.circle(frame, (cx, cy), 8, (0,0,255), -1)

#             x_min = np.min(group[:,0])
#             y_min = np.min(group[:,1])
#             x_max = np.max(group[:,0])
#             y_max = np.max(group[:,1])

#             cv2.rectangle(frame,
#                           (x_min-25, y_min-25),
#                           (x_max+25, y_max+25),
#                           (0,0,255), 3)

#             cv2.putText(frame, "GATHERING ALERT",
#                         (x_min, y_min-30),
#                         cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)

#     # -------------------------------------
#     # FPS calculation
#     # -------------------------------------
#     curr_time = time.time()
#     fps_val = 1/(curr_time-prev_time)
#     prev_time = curr_time

#     # -------------------------------------
#     # UI Text
#     # -------------------------------------
#     cv2.putText(frame, f"People: {len(person_boxes)}", (20,40),
#                 cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)

#     cv2.putText(frame, f"Cross Count: {counter}", (20,70),
#                 cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)

#     cv2.putText(frame, f"FPS: {int(fps_val)}", (20,100),
#                 cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 2)

#     cv2.putText(frame, f"Gather Timer: {gather_timer}", (20,130),
#                 cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,200), 1)

#     # -------------------------------------
#     # Show + Save
#     # -------------------------------------
#     cv2.imshow("Smart Crowd Detection", frame)
#     out.write(frame)

#     if cv2.waitKey(1) == 27:
#         break


# # =====================================================
# # CLEANUP
# # =====================================================

# cap.release()
# out.release()
# cv2.destroyAllWindows()

# print("Finished. Output saved as:", OUTPUT_PATH)
from ultralytics import YOLO
import argparse
import cv2
import numpy as np
import time
import json
from pathlib import Path


def parse_args():
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Crowd gathering detection")
    parser.add_argument("--video", default=str(root / "3.mp4"), help="Input video path")
    parser.add_argument("--model", default=str(root / "yolov8s.pt"), help="YOLO model path")
    parser.add_argument("--output", default=str(root / "crowd_gathering.mp4"), help="Output video path")
    parser.add_argument("--gather-threshold", type=float, default=50.0, help="Distance threshold for gathering")
    parser.add_argument("--line-y", type=int, default=400, help="Line crossing Y position")
    parser.add_argument("--display", action="store_true", help="Show live OpenCV window")
    return parser.parse_args()


def detect_gatherings(boxes, threshold=50):
    centers = [(int((x1 + x2) / 2), int((y1 + y2) / 2)) for x1, y1, x2, y2 in boxes]
    gatherings = []
    for i, c1 in enumerate(centers):
        for j, c2 in enumerate(centers):
            if i != j:
                dist = np.sqrt((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2)
                if dist < threshold:
                    gatherings.append((c1, c2))
    return gatherings


def create_video_writer(path, fps, frame_width, frame_height):
    codec_priority = ("avc1", "H264", "X264", "mp4v")
    for codec in codec_priority:
        writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*codec), fps, (frame_width, frame_height))
        if writer.isOpened():
            return writer, codec
        writer.release()
    raise RuntimeError(f"Unable to initialize output writer: {path}")


def main():
    args = parse_args()
    model = YOLO(args.model)

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video file: {args.video}")

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 20
    out, output_codec = create_video_writer(args.output, fps, frame_width, frame_height)

    count_line_position = args.line_y
    offset = 6
    counter = 0
    gather_events = 0

    line_cooldown = 0
    gather_timer = 0
    GATHER_TIME_THRESHOLD = 25
    heatmap = np.zeros((frame_height, frame_width), dtype=np.float32)
    prev_time = time.time()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame)
        person_boxes = []
        centers = []

        for box in results[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cls = int(box.cls[0])

            if cls == 0:
                x1 = max(0, min(x1, frame_width - 1))
                y1 = max(0, min(y1, frame_height - 1))
                x2 = max(0, min(x2, frame_width - 1))
                y2 = max(0, min(y2, frame_height - 1))

                person_boxes.append((x1, y1, x2, y2))
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                centers.append((cx, cy))

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                heatmap *= 0.90
                for hx, hy in centers:
                    cv2.circle(heatmap, (hx, hy), 20, 1, -1)

        if line_cooldown > 0:
            line_cooldown -= 1

        for cx, cy in centers:
            if abs(cy - count_line_position) < offset and line_cooldown == 0:
                counter += 1
                line_cooldown = 10

        cv2.line(frame, (25, count_line_position), (frame_width - 25, count_line_position), (255, 127, 0), 3)
        cv2.putText(frame, f"Human Count: {counter}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 244, 0), 2)

        gatherings = detect_gatherings(person_boxes, threshold=args.gather_threshold)
        if gatherings:
            gather_timer += 1
        else:
            gather_timer = max(0, gather_timer - 2)

        if gather_timer > GATHER_TIME_THRESHOLD:
            gather_events += 1
            for c1, c2 in gatherings:
                cv2.circle(frame, c1, 8, (0, 0, 255), -1)
                cv2.circle(frame, c2, 8, (0, 0, 255), -1)
                cv2.line(frame, c1, c2, (255, 0, 0), 2)
                cv2.putText(frame, "Gathering!", c1, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

        heat_blur = cv2.GaussianBlur(heatmap, (0, 0), 15)
        heat_norm = cv2.normalize(heat_blur, None, 0, 255, cv2.NORM_MINMAX)
        heat_color = cv2.applyColorMap(heat_norm.astype(np.uint8), cv2.COLORMAP_JET)
        frame = cv2.addWeighted(frame, 0.7, heat_color, 0.3, 0)

        curr_time = time.time()
        fps_val = 1 / (curr_time - prev_time)
        prev_time = curr_time
        cv2.putText(frame, f"FPS: {int(fps_val)}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        out.write(frame)
        if args.display:
            cv2.imshow("YOLOv8 Human Detection", frame)
            if cv2.waitKey(1) == 27:
                break

    cap.release()
    out.release()
    if args.display:
        cv2.destroyAllWindows()
    print(json.dumps({
        "service": "CROWD_GATHERING",
        "status": "COMPLETED",
        "lineCrossCount": counter,
        "gatherEventFrames": gather_events,
        "videoCodec": output_codec,
        "output": str(Path(args.output).resolve())
    }))


if __name__ == "__main__":
    main()
