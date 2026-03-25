# # # # import cv2
# # # # import numpy as np
# # # # import joblib
# # import smtplib
# # from email.mime.text import MIMEText

# # # # def preprocess_frame(frame):
# # # #     resized_frame = cv2.resize(frame, (224, 224))
# # # #     gray_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2GRAY)
# # # #     normalized_frame = gray_frame / 255.0
# # # #     return normalized_frame


# # # # def extract_features(frames, target_feature_size):
# # # #     features = []

# # # #     # compute resizing side length dynamically
# # # #     side = int(np.sqrt(target_feature_size))
# # # #     if side * side != target_feature_size:
# # # #         side = int(np.sqrt(target_feature_size + 1))

# # # #     for i in range(len(frames) - 1):
# # # #         flow = cv2.calcOpticalFlowFarneback(frames[i], frames[i + 1], None,
# # # #                                             0.5, 3, 15, 3, 5, 1.2, 0)
# # # #         mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
# # # #         mag_resized = cv2.resize(mag, (side, side))
# # # #         flat = mag_resized.flatten()

# # # #         # crop/pad to match exact model features
# # # #         if len(flat) > target_feature_size:
# # # #             flat = flat[:target_feature_size]
# # # #         elif len(flat) < target_feature_size:
# # # #             flat = np.pad(flat, (0, target_feature_size - len(flat)), 'constant')
# # # #         features.append(flat)

# # # #     return np.array(features)


# # # # def further_processing(predictions):
# # # #     threshold = 0.5
# # # #     processed_predictions = predictions > threshold
# # # #     return processed_predictions.astype(int)


# # # # def main():
# # # #     # Load model
# # # #     mdt_model = joblib.load('model.pkl')
# # # #     target_feature_size = getattr(mdt_model, 'n_features_in_', 476)
# # # #     print(f"Model expects {target_feature_size} features per sample")

# # # #     # Video path
# # # #     video_path = '/Users/saidharahasrao/Downloads/Crowd-Anomaly-Detection-master/3.mp4'
# # # #     cap = cv2.VideoCapture(video_path)
# # # #     if not cap.isOpened():
# # # #         print("Error: Cannot open video.")
# # # #         return

# # # #     frames = []
# # # #     display_frames = []
# # # #     while True:
# # # #         ret, frame = cap.read()
# # # #         if not ret:
# # # #             break
# # # #         frames.append(preprocess_frame(frame))
# # # #         display_frames.append(cv2.resize(frame, (640, 480)))
# # # #     cap.release()

# # # #     print(f"Total frames extracted: {len(frames)}")

# # # #     if len(frames) < 2:
# # # #         print("Not enough frames for optical flow.")
# # # #         return

# # # #     # Extract and predict
# # # #     features = extract_features(frames, target_feature_size)
# # # #  # Use log-likelihood scores for anomaly detection
# # # #     log_probs = mdt_model.score_samples(features)

# # # # # Set adaptive threshold (lower score = more likely anomaly)
# # # #     threshold = np.percentile(log_probs, 5)  # bottom 5% = anomalies
# #             # send_email_alert()
# # # #     processed_predictions = (log_probs < threshold).astype(int)

# # # #     print(f"Anomaly threshold: {threshold}")
# # # #     print(f"Detected anomalies: {np.sum(processed_predictions)} / {len(processed_predictions)}")


# # # #     print("Processed Predictions:", processed_predictions.shape)

# # # #     # Optional: save output video
# # # #     out_path = "anomaly_output.mp4"
# # # #     fourcc = cv2.VideoWriter_fourcc(*'mp4v')
# # # #     out = cv2.VideoWriter(out_path, fourcc, 20.0, (640, 480))

# # # #     # Display with anomaly highlights
# # # #     for i in range(len(processed_predictions)):
# # # #         frame = display_frames[i].copy()
# # # #         if processed_predictions[i] == 1:
# # # #             # Draw red border for anomaly
# # # #             cv2.rectangle(frame, (0, 0), (639, 479), (0, 0, 255), 10)
# # # #             cv2.putText(frame, "ANOMALY DETECTED!", (50, 50),
# # # #                         cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
# # # #         else:
# # # #             cv2.rectangle(frame, (0, 0), (639, 479), (0, 255, 0), 3)
# # # #             cv2.putText(frame, "Normal", (50, 50),
# # # #                         cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)

# # # #         cv2.imshow("Crowd Anomaly Detection", frame)
# # # #         out.write(frame)

# # # #         if cv2.waitKey(1) & 0xFF == ord('q'):
# # # #             break

# # # #     out.release()
# # # #     cv2.destroyAllWindows()
# # # #     print(f"✅ Visualization complete. Saved to: {out_path}")


# # # # if __name__ == '__main__':
# # # #     main()
# # import cv2
# # import numpy as np
# # import joblib
# # from playsound import playsound
# # import smtplib
# # from email.mime.text import MIMEText

# # # def send_email_alert():
# #     # Fill in your Gmail credentials and recipient
# #     # Email notification functionality is disabled.
# #     # To re-enable, uncomment the code below and fill in credentials.
# #     # gmail_user = 'sdr302760@gmail.com'
# #     # gmail_app_password = 'mzhlamegulecuqpn'
# #     # to_email = 'dharahas04@gmail.com'
# #     # subject = 'Crowd Anomaly Detected!'
# #     # body = 'An anomaly was detected by your Anomaly Detector.'
# #     # msg = MIMEText(body)
# #     # msg['Subject'] = subject
# #     # msg['From'] = gmail_user
# #     # msg['To'] = to_email
# #     # print('Attempting to send anomaly email alert...')
# #     # try:
# #     #     server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
# #     #     server.login(gmail_user, gmail_app_password)
# #     #     server.sendmail(gmail_user, [to_email], msg.as_string())
# #     #     server.quit()
# #     #     print('Email alert sent successfully!')
# #     # except Exception as e:
# #     #     import traceback
# #     #     print('Email send error:')
# #     #     traceback.print_exc()

# # def preprocess_frame(frame):
# #     resized_frame = cv2.resize(frame, (224, 224))
# #     gray_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2GRAY)
# #     normalized_frame = gray_frame / 255.0
# #     return normalized_frame
# #     resized_frame = cv2.resize(frame, (224, 224))
# #     gray_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2GRAY)
# #     normalized_frame = gray_frame / 255.0
# #     return normalized_frame


# # def extract_features(frames, target_feature_size):
# #     features = []

# #     # compute resizing side length dynamically
# #     side = int(np.sqrt(target_feature_size))
# #     if side * side != target_feature_size:
# #         side = int(np.sqrt(target_feature_size + 1))

# #     for i in range(len(frames) - 1):
# #         flow = cv2.calcOpticalFlowFarneback(frames[i], frames[i + 1], None,
# #                                             0.5, 3, 15, 3, 5, 1.2, 0)
# #         mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
# #         mag_resized = cv2.resize(mag, (side, side))
# #         flat = mag_resized.flatten()

# #         # crop/pad to match exact model features
# #         if len(flat) > target_feature_size:
# #             flat = flat[:target_feature_size]
# #         elif len(flat) < target_feature_size:
# #             flat = np.pad(flat, (0, target_feature_size - len(flat)), 'constant')
# #         features.append(flat)

# #     return np.array(features)


# # def main():
# #     # Load model
# #     mdt_model = joblib.load('model.pkl')
# #     target_feature_size = getattr(mdt_model, 'n_features_in_', 476)
# #     print(f"Model expects {target_feature_size} features per sample")

# #     # Video path
# #     video_path = '/Users/saidharahasrao/Downloads/Crowd-Anomaly-Detection-master/1.mp4'
# #     cap = cv2.VideoCapture(video_path)
# #     if not cap.isOpened():
# #         print("Error: Cannot open video.")
# #         return

# #     frames = []
# #     display_frames = []
# #     while True:
# #         ret, frame = cap.read()
# #         if not ret:
# #             break
# #         frames.append(preprocess_frame(frame))
# #         display_frames.append(cv2.resize(frame, (640, 480)))
# #     cap.release()

# #     print(f"Total frames extracted: {len(frames)}")

# #     if len(frames) < 2:
# #         print("Not enough frames for optical flow.")
# #         return

# #     # Extract and predict
# #     features = extract_features(frames, target_feature_size)
# #     log_probs = mdt_model.score_samples(features)

# #     # Adaptive threshold (bottom 10% = anomalies, more sensitive)
# #     threshold = np.percentile(log_probs, 10)
# #     print(f"Log-likelihood scores: {log_probs}")
# #     print(f"Anomaly threshold (10th percentile): {threshold}")
# #     processed_predictions = (log_probs < threshold).astype(int)
# #     print(f"Detected anomalies: {np.sum(processed_predictions)} / {len(processed_predictions)}")

# #     # Temporal smoothing: keep anomalies visible for 'linger_frames' frames
# #     linger_frames = 10
# #     smoothed_predictions = processed_predictions.copy()

# #     for i in range(1, len(processed_predictions)):
# #         if processed_predictions[i] == 1:
# #             smoothed_predictions[i:i + linger_frames] = 1

# #     # Save output video
# #     out_path = "anomaly_output.mp4"
# #     fourcc = cv2.VideoWriter_fourcc(*'mp4v')
# #     out = cv2.VideoWriter(out_path, fourcc, 20.0, (640, 480))

# #     print("▶️ Starting visualization... Press 'q' to quit.")

# #     # Alarm sound setup
# #     alarm_path = '/Users/saidharahasrao/Downloads/Crowd-Anomaly-Detection-master/preview.mp3'  # Place preview.mp3 in the project directory
# #     alarm_played = False

# #     # Display with persistent anomaly highlights
# #     prev_anomaly = 0
# #     for i in range(len(smoothed_predictions)):
# #         frame = display_frames[i].copy()

# #         if smoothed_predictions[i] == 1:
# #             # Draw bold red border for anomaly
# #             cv2.rectangle(frame, (0, 0), (639, 479), (0, 0, 255), 8)
# #             cv2.putText(frame, "ANOMALY DETECTED!", (50, 60),
# #                         cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 4)
# #             # Play alarm sound only when anomaly status transitions from normal to anomaly
# #             if prev_anomaly == 0:
# #                 print('Anomaly detected: triggering alarm notification.')
# #                 try:
# #                     playsound(alarm_path, block=False)
# #                 except Exception as e:
# #                     print(f"Alarm sound error: {e}")
# #                 # send_email_alert()  # Email notification is disabled
# #         else:
# #             # Subtle green border for normal
# #             cv2.rectangle(frame, (0, 0), (639, 479), (0, 255, 0), 3)
# #             cv2.putText(frame, "Normal", (50, 60),
# #                         cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)

# #         prev_anomaly = smoothed_predictions[i]
# #         out.write(frame)
# #         cv2.imshow("Crowd Anomaly Detection", frame)

# #         if cv2.waitKey(1) & 0xFF == ord('q'):
# #             break

# #     out.release()
# #     cv2.destroyAllWindows()
# #     print(f"✅ Visualization complete. Saved to: {out_path}")


# # if __name__ == '__main__':
# #     main()
# # # import cv2
# # # import numpy as np
# # # import joblib
# # # import time

# # # def preprocess_frame(frame):
# # #     resized_frame = cv2.resize(frame, (224, 224))
# # #     gray_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2GRAY)
# # #     normalized_frame = gray_frame / 255.0
# # #     return normalized_frame


# # # def extract_features(frames, target_feature_size):
# # #     features = []
# # #     side = int(np.sqrt(target_feature_size))
# # #     if side * side != target_feature_size:
# # #         side = int(np.sqrt(target_feature_size + 1))

# # #     for i in range(len(frames) - 1):
# # #         flow = cv2.calcOpticalFlowFarneback(frames[i], frames[i + 1], None,
# # #                                             0.5, 3, 15, 3, 5, 1.2, 0)
# # #         mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
# # #         mag_resized = cv2.resize(mag, (side, side))
# # #         flat = mag_resized.flatten()

# # #         # match feature size
# # #         if len(flat) > target_feature_size:
# # #             flat = flat[:target_feature_size]
# # #         elif len(flat) < target_feature_size:
# # #             flat = np.pad(flat, (0, target_feature_size - len(flat)), 'constant')
# # #         features.append(flat)

# # #     return np.array(features)


# # # def draw_status_overlay(frame, status_text, color, alpha=0.4):
# # #     """Draw semi-transparent overlay and text"""
# # #     overlay = frame.copy()
# # #     cv2.rectangle(overlay, (0, 0), (639, 479), color, -1)
# # #     return cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)


# # # def draw_progress_bar(frame, progress, color=(255, 255, 255)):
# # #     bar_width = int(600 * progress)
# # #     cv2.rectangle(frame, (20, 440), (20 + bar_width, 460), color, -1)
# # #     cv2.rectangle(frame, (20, 440), (620, 460), (180, 180, 180), 2)
# # #     return frame


# # # def main():
# # #     # Load model
# # #     mdt_model = joblib.load('model.pkl')
# # #     target_feature_size = getattr(mdt_model, 'n_features_in_', 476)
# # #     print(f"Model expects {target_feature_size} features per sample")

# # #     # Video path
# # #     video_path = '/Users/saidharahasrao/Downloads/Crowd-Anomaly-Detection-master/4.mp4'
# # #     cap = cv2.VideoCapture(video_path)
# # #     if not cap.isOpened():
# # #         print("Error: Cannot open video.")
# # #         return

# # #     frames, display_frames = [], []
# # #     while True:
# # #         ret, frame = cap.read()
# # #         if not ret:
# # #             break
# # #         frames.append(preprocess_frame(frame))
# # #         display_frames.append(cv2.resize(frame, (640, 480)))
# # #     cap.release()

# # #     print(f"Total frames extracted: {len(frames)}")

# # #     if len(frames) < 2:
# # #         print("Not enough frames for optical flow.")
# # #         return

# # #     # Feature extraction + prediction
# # #     features = extract_features(frames, target_feature_size)
# # #     log_probs = mdt_model.score_samples(features)

# # #     threshold = np.percentile(log_probs, 5)
# # #     processed_predictions = (log_probs < threshold).astype(int)
# # #     print(f"Anomaly threshold: {threshold}")
# # #     print(f"Detected anomalies: {np.sum(processed_predictions)} / {len(processed_predictions)}")

# # #     # Smooth anomalies visually
# # #     linger_frames = 10
# # #     smoothed_predictions = processed_predictions.copy()
# # #     for i in range(1, len(processed_predictions)):
# # #         if processed_predictions[i] == 1:
# # #             smoothed_predictions[i:i + linger_frames] = 1

# # #     # Output setup
# # #     out_path = "anomaly_output.mp4"
# # #     fourcc = cv2.VideoWriter_fourcc(*'mp4v')
# # #     out = cv2.VideoWriter(out_path, fourcc, 20.0, (640, 480))
# # #     total_frames = len(smoothed_predictions)

# # #     print("▶️ Starting cinematic visualization... Press 'q' to quit.")

# # #     # Visualization
# # #     for i, frame in enumerate(display_frames[:len(smoothed_predictions)]):
# # #         frame = frame.copy()
# # #         progress = (i + 1) / total_frames

# # #         if smoothed_predictions[i] == 1:
# # #             frame = draw_status_overlay(frame, "ANOMALY DETECTED", (0, 0, 255))
# # #             cv2.putText(frame, "⚠️  ANOMALY DETECTED", (80, 100),
# # #                         cv2.FONT_HERSHEY_DUPLEX, 1.2, (255, 255, 255), 3)
# # #             cv2.rectangle(frame, (0, 0), (639, 479), (0, 0, 255), 6)
# # #         else:
# # #             frame = draw_status_overlay(frame, "NORMAL", (0, 255, 0))
# # #             cv2.putText(frame, "Normal", (100, 100),
# # #                         cv2.FONT_HERSHEY_DUPLEX, 1.2, (255, 255, 255), 3)
# # #             cv2.rectangle(frame, (0, 0), (639, 479), (0, 255, 0), 4)

# # #         # Progress bar
# # #         draw_progress_bar(frame, progress)

# # #         # Add subtle watermark
# # #         cv2.putText(frame, "Crowd Anomaly Detector", (320, 470),
# # #                     cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)

# # #         # Smooth fade for anomaly frames
# # #         if smoothed_predictions[i] == 1:
# # #             for fade in np.linspace(0.6, 1, 3):
# # #                 faded = cv2.addWeighted(frame, fade, np.zeros_like(frame), 1 - fade, 0)
# # #                 cv2.imshow("Crowd Anomaly Detection", faded)
# # #                 out.write(faded)
# # #                 if cv2.waitKey(5) & 0xFF == ord('q'):
# # #                     break
# # #         else:
# # #             cv2.imshow("Crowd Anomaly Detection", frame)
# # #             out.write(frame)

# # #         if cv2.waitKey(1) & 0xFF == ord('q'):
# # #             break

# # #     out.release()
# # #     cv2.destroyAllWindows()
# # #     print(f"✅ Cinematic visualization complete. Saved to: {out_path}")


# # # if __name__ == '__main__':
# # #     main()
# import cv2
# import numpy as np
# import joblib
# import os
# from collections import deque

# # ================= CONFIG =================
# VIDEO_PATH = "4.mp4"
# MODEL_PATH = "model.pkl"
# OUTPUT_VIDEO = "anomaly_output.mp4"
# WINDOW_SIZE = 15          # temporal voting window
# ANOMALY_RATIO = 0.6       # % of window frames required to mark anomaly
# # =========================================


# def preprocess_frame(frame):
#     resized = cv2.resize(frame, (224, 224))
#     gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
#     return gray / 255.0


# def extract_advanced_features(frames, target_feature_size):
#     features = []

#     side = int(np.sqrt(target_feature_size))
#     if side * side != target_feature_size:
#         side += 1

#     for i in range(len(frames) - 1):
#         flow = cv2.calcOpticalFlowFarneback(
#             frames[i], frames[i + 1],
#             None, 0.5, 3, 15, 3, 5, 1.2, 0
#         )

#         mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])

#         # --- Advanced motion statistics ---
#         mean_motion = np.mean(mag)
#         var_motion = np.var(mag)
#         max_motion = np.max(mag)

#         mag_resized = cv2.resize(mag, (side, side))
#         flat = mag_resized.flatten()

#         # Adjust feature length
#         if len(flat) > target_feature_size - 3:
#             flat = flat[:target_feature_size - 3]
#         elif len(flat) < target_feature_size - 3:
#             flat = np.pad(flat, (0, target_feature_size - 3 - len(flat)))

#         combined = np.concatenate([flat, [mean_motion, var_motion, max_motion]])
#         features.append(combined)

#     return np.array(features)


# def robust_threshold(scores):
#     """ MAD-based robust threshold """
#     median = np.median(scores)
#     mad = np.median(np.abs(scores - median)) + 1e-6
#     threshold = median - 2.5 * mad
#     return threshold


# def main():
#     print("🔹 Loading model...")
#     model = joblib.load(MODEL_PATH)
#     feature_size = getattr(model, "n_features_in_", 476)
#     print(f"Model expects {feature_size} features")

#     if not os.path.exists(VIDEO_PATH):
#         print("❌ Video not found")
#         return

#     cap = cv2.VideoCapture(VIDEO_PATH)
#     frames, display_frames = [], []

#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             break
#         frames.append(preprocess_frame(frame))
#         display_frames.append(cv2.resize(frame, (640, 480)))

#     cap.release()

#     if len(frames) < 2:
#         print("❌ Not enough frames")
#         return

#     print("🔹 Extracting advanced features...")
#     features = extract_advanced_features(frames, feature_size)

#     print("🔹 Scoring anomalies...")
#     scores = model.score_samples(features)

#     threshold = robust_threshold(scores)
#     raw_preds = (scores < threshold).astype(int)

#     # -------- Temporal voting (VERY IMPORTANT) --------
#     vote_window = deque(maxlen=WINDOW_SIZE)
#     final_preds = []

#     for p in raw_preds:
#         vote_window.append(p)
#         ratio = sum(vote_window) / len(vote_window)
#         final_preds.append(1 if ratio >= ANOMALY_RATIO else 0)

#     print(f"Detected anomalies: {sum(final_preds)}")

#     # -------- Visualization --------
#     out = cv2.VideoWriter(
#         OUTPUT_VIDEO,
#         cv2.VideoWriter_fourcc(*"mp4v"),
#         20,
#         (640, 480)
#     )

#     for i, pred in enumerate(final_preds):
#         frame = display_frames[i].copy()

#         confidence = abs(scores[i] - threshold)
#         confidence = min(confidence * 100, 99)

#         if pred == 1:
#             cv2.rectangle(frame, (0, 0), (639, 479), (0, 0, 255), 6)
#             cv2.putText(frame, f"ANOMALY ({confidence:.1f}%)",
#                         (40, 60), cv2.FONT_HERSHEY_SIMPLEX,
#                         1.2, (0, 0, 255), 3)
#         else:
#             cv2.rectangle(frame, (0, 0), (639, 479), (0, 255, 0), 3)
#             cv2.putText(frame, "Normal",
#                         (40, 60), cv2.FONT_HERSHEY_SIMPLEX,
#                         1.1, (0, 255, 0), 3)

#         out.write(frame)
#         cv2.imshow("Advanced Crowd Anomaly Detection", frame)

#         if cv2.waitKey(1) & 0xFF == ord("q"):
#             break

#     out.release()
#     cv2.destroyAllWindows()
#     print("✅ Advanced anomaly detection complete!")


# if __name__ == "__main__":
#     main()
import cv2
import numpy as np
import joblib
import os
import argparse
import json
from collections import deque

# ================= CONFIG =================
VIDEO_PATH = "1.mp4"              # input video
MODEL_PATH = "model.pkl"          # trained GMM model
OUTPUT_VIDEO = "anomaly_output.mp4"

WINDOW_SIZE = 10                  # temporal voting window
ANOMALY_RATIO = 0.3               # % votes needed for anomaly
MAD_MULTIPLIER = 3.5              # robustness factor
FPS = 20
# =========================================
TRAIN_SCORES_PATH = "train_scores.npy"   # <-- ADD THIS


# ---------- PREPROCESS ----------
def preprocess_frame(frame):
    frame = cv2.resize(frame, (224, 224))
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return gray / 255.0


# ---------- FEATURE EXTRACTION ----------
def extract_advanced_features(frames, target_feature_size):
    """
    Extract optical-flow-based features + motion statistics.
    Ensures feature size EXACTLY matches trained model.
    """
    EXTRA_FEATURES = 3  # mean, variance, max
    BASE_FEATURES = target_feature_size - EXTRA_FEATURES

    features = []
    side = int(np.sqrt(BASE_FEATURES))
    if side * side != BASE_FEATURES:
        side += 1

    for i in range(len(frames) - 1):
        flow = cv2.calcOpticalFlowFarneback(
            frames[i], frames[i + 1],
            None, 0.5, 3, 15, 3, 5, 1.2, 0
        )

        mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])

        # motion statistics
        mean_motion = np.mean(mag)
        var_motion = np.var(mag)
        max_motion = np.max(mag)

        mag_resized = cv2.resize(mag, (side, side))
        flat = mag_resized.flatten()

        # enforce correct feature size
        if len(flat) > BASE_FEATURES:
            flat = flat[:BASE_FEATURES]
        elif len(flat) < BASE_FEATURES:
            flat = np.pad(flat, (0, BASE_FEATURES - len(flat)))

        combined = np.concatenate(
            [flat, [mean_motion, var_motion, max_motion]]
        )
        features.append(combined)

    return np.array(features)


# ---------- ROBUST THRESHOLD ----------
def mad_threshold(scores, multiplier=MAD_MULTIPLIER):
    """
    Median Absolute Deviation (robust to noise & outliers)
    """
    median = np.median(scores)
    mad = np.median(np.abs(scores - median)) + 1e-6
    return median - multiplier * mad


# ---------- MAIN PIPELINE ----------
def anomaly_confidence_percent(score, threshold, mad, score_std):
    """
    Convert anomaly strength into a stable 0-99 confidence.
    Uses robust deviation from threshold to avoid flat 0.0% outputs.
    """
    robust_scale = max(float(mad), 1e-6)
    std_scale_cap = max(float(score_std) * 2.0, 1e-6)
    # Cap over-large MAD from train distribution so confidence remains informative on current video.
    scale = min(robust_scale, std_scale_cap)
    deviation = max(0.0, (threshold - score) / scale)
    confidence = 100.0 * (1.0 - np.exp(-deviation))
    return float(np.clip(confidence, 0.0, 99.0))


def sanitize_confidence(value, default=1.0, minimum=1.0, maximum=99.0):
    """
    Keep confidence values numeric and bounded for clean overlay text.
    """
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = float(default)
    if not np.isfinite(numeric):
        numeric = float(default)
    return float(np.clip(numeric, minimum, maximum))


def create_video_writer(path, fps, frame_size):
    codec_priority = ("avc1", "H264", "X264", "mp4v")
    for codec in codec_priority:
        writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*codec), fps, frame_size)
        if writer.isOpened():
            return writer, codec
        writer.release()
    raise RuntimeError(f"Unable to initialize output writer: {path}")


def main(video_path, model_path, output_video, train_scores_path, display=False):
    print("🔹 Loading model...")
    model = joblib.load(model_path)
    feature_size = model.n_features_in_
    print(f"Model feature size: {feature_size}")

    if not os.path.exists(video_path):
        print(json.dumps({
            "service": "CROWD_ANOMALY",
            "status": "FAILED",
            "reason": "Input video file not found",
            "videoPath": video_path
        }))
        raise SystemExit(1)

    cap = cv2.VideoCapture(video_path)
    frames = []
    display_frames = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(preprocess_frame(frame))
        display_frames.append(cv2.resize(frame, (640, 480)))

    cap.release()

    if len(frames) < 2:
        print(json.dumps({
            "service": "CROWD_ANOMALY",
            "status": "FAILED",
            "reason": "Not enough frames for optical flow",
            "framesExtracted": len(frames)
        }))
        raise SystemExit(1)

    print("🔹 Extracting features...")
    features = extract_advanced_features(frames, feature_size)

    print("🔹 Scoring with GMM...")
    scores = model.score_samples(features)

    # threshold = mad_threshold(scores)
    # ---------- ADAPTIVE THRESHOLD ----------
        # ---------- TRAIN-BASED THRESHOLD (NO TEST LEAKAGE) ----------
    threshold_mad = None
    if os.path.exists(train_scores_path):
        train_scores = np.load(train_scores_path)
        median = np.median(train_scores)
        threshold_mad = np.median(np.abs(train_scores - median)) + 1e-6
        threshold = median - MAD_MULTIPLIER * threshold_mad
        print("✅ Using training-based threshold")
    else:
        threshold = mad_threshold(scores)
        median = np.median(scores)
        threshold_mad = np.median(np.abs(scores - median)) + 1e-6
        print("⚠️ Training scores not found, using test-based threshold")
    score_std = float(np.std(scores))
    print("Threshold:", threshold)
    print("Score range:", np.min(scores), np.mean(scores), np.max(scores))
    print("Score std:", score_std)

    raw_preds = (scores < threshold).astype(int)
    # raw_preds = np.ones_like(scores, dtype=int)
    # print("⚠️ FORCING ALL FRAMES AS ANOMALY")


    # ---------- TEMPORAL VOTING ----------
    vote_window = deque(maxlen=WINDOW_SIZE)
    final_preds = []
    final_vote_ratios = []

    for p in raw_preds:
        vote_window.append(p)
        ratio = sum(vote_window) / len(vote_window)
        final_vote_ratios.append(ratio)
        final_preds.append(1 if ratio >= ANOMALY_RATIO else 0)

    print(f"✅ Total anomalies detected: {sum(final_preds)}")

    # ---------- VISUALIZATION ----------
    output_dir = os.path.dirname(output_video)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    try:
        out, output_codec = create_video_writer(output_video, FPS, (640, 480))
    except Exception:
        print(json.dumps({
            "service": "CROWD_ANOMALY",
            "status": "FAILED",
            "reason": "Unable to open output video writer",
            "outputVideo": output_video
        }))
        raise SystemExit(1)

    anomaly_conf_trace = []
    normal_conf_trace = []

    for i, pred in enumerate(final_preds):
        if i >= len(display_frames):
            break

        frame = display_frames[i].copy()

        anomaly_confidence = sanitize_confidence(
            anomaly_confidence_percent(scores[i], threshold, threshold_mad, score_std),
            default=0.0,
            minimum=0.0
        )
        normal_confidence = sanitize_confidence(100.0 - anomaly_confidence, default=60.0)
        vote_confidence = sanitize_confidence(
            final_vote_ratios[i] * 100.0,
            default=0.0,
            minimum=0.0
        )
        if pred == 1:
            # Avoid misleading anomaly labels like 0.0%
            anomaly_confidence = sanitize_confidence(
                max(5.0, anomaly_confidence, vote_confidence),
                default=5.0,
                minimum=5.0
            )
            anomaly_conf_trace.append(anomaly_confidence)
        else:
            normal_confidence = sanitize_confidence(
                max(
                    normal_confidence,
                    float(np.clip((1.0 - final_vote_ratios[i]) * 100.0, 1.0, 99.0))
                ),
                default=60.0
            )
            normal_conf_trace.append(normal_confidence)

        if pred == 1:
            cv2.rectangle(frame, (0, 0), (639, 479), (0, 0, 255), 6)
            cv2.putText(
                frame,
                f"ANOMALY ({anomaly_confidence:.1f}%)",
                (40, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2,
                (0, 0, 255),
                3
            )
        else:
            cv2.rectangle(frame, (0, 0), (639, 479), (0, 255, 0), 3)
            cv2.putText(
                frame,
                f"Normal ({normal_confidence:.1f}%)",
                (40, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.1,
                (0, 255, 0),
                3
            )

        out.write(frame)
        if display:
            cv2.imshow("Advanced Crowd Anomaly Detection", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    out.release()
    if display:
        cv2.destroyAllWindows()
    print(f"🎉 Output saved as {output_video}")
    processed_frames = min(len(final_preds), len(display_frames))
    anomaly_frames = int(sum(final_preds[:processed_frames])) if processed_frames > 0 else 0
    anomaly_ratio = (anomaly_frames / processed_frames * 100.0) if processed_frames > 0 else 0.0
    summary = {
        "service": "CROWD_ANOMALY",
        "status": "COMPLETED",
        "framesProcessed": int(processed_frames),
        "anomalyFrames": int(anomaly_frames),
        "anomalyRatioPct": round(float(anomaly_ratio), 2),
        "maxAnomalyConfidencePct": round(float(max(anomaly_conf_trace) if anomaly_conf_trace else 0.0), 2),
        "avgAnomalyConfidencePct": round(float(np.mean(anomaly_conf_trace)) if anomaly_conf_trace else 0.0, 2),
        "avgNormalConfidencePct": round(float(np.mean(normal_conf_trace)) if normal_conf_trace else 0.0, 2),
        "threshold": round(float(threshold), 6),
        "scoreStd": round(float(score_std), 6),
        "videoCodec": output_codec,
        "outputVideo": output_video
    }
    print(json.dumps(summary))


def parse_args():
    parser = argparse.ArgumentParser(description="Crowd anomaly detection")
    parser.add_argument("--video", default=VIDEO_PATH, help="Input video path")
    parser.add_argument("--model", default=MODEL_PATH, help="Model path")
    parser.add_argument("--output", default=OUTPUT_VIDEO, help="Output video path")
    parser.add_argument("--train-scores", default=TRAIN_SCORES_PATH, help="Training scores .npy file path")
    parser.add_argument("--display", action="store_true", help="Show live OpenCV window during processing")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(
        video_path=args.video,
        model_path=args.model,
        output_video=args.output,
        train_scores_path=args.train_scores,
        display=args.display
    )
