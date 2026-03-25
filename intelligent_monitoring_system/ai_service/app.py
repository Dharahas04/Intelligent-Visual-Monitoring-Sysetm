from flask import Flask, request, jsonify
from flask_cors import CORS
from tensorflow.keras.models import load_model
import numpy as np
import cv2
import base64
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize Flask App
app = Flask(__name__)
CORS(app, resources={r"/detect": {"origins": "http://localhost:3000"}})

# --- Load Your Models (Do this once when the server starts) ---
try:
    logging.info("Loading face detector model...")
    prototxtPath = "models/deploy.prototxt"
    weightsPath = "models/res10_300x300_ssd_iter_140000.caffemodel"
    faceNet = cv2.dnn.readNet(prototxtPath, weightsPath)

    logging.info("Loading face mask detector model...")
    maskNet = load_model("models/mask_detector_pretrained.h5")
    logging.info("Models loaded successfully!")
except Exception as e:
    logging.error(f"Error loading models: {e}")
    faceNet = None
    maskNet = None
# -------------------------------------------------------------

# Define the API endpoint for mask detection
@app.route("/detect", methods=["POST"])
def detect_mask():
    if not faceNet or not maskNet:
        return jsonify({"error": "Models are not loaded, check server logs."}), 500
        
    data = request.get_json()
    if "image" not in data:
        return jsonify({"error": "No image data provided"}), 400

    try:
        # Decode the base64 image
        img_data = base64.b64decode(data['image'])
        np_arr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({"error": "Could not decode image"}), 400

        # --- Your Detection Logic ---
        (h, w) = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), (104.0, 177.0, 123.0))

        faceNet.setInput(blob)
        detections = faceNet.forward()
        results = []

        # Loop over the detections
        for i in range(0, detections.shape[2]):
            confidence = detections[0, 0, i, 2]

            if confidence > 0.5:
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (startX, startY, endX, endY) = box.astype("int")
                (startX, startY) = (max(0, startX), max(0, startY))
                (endX, endY) = (min(w - 1, endX), min(h - 1, endY))

                face = frame[startY:endY, startX:endX]
                
                # --- ADDED ROBUSTNESS CHECK ---
                # If face region is invalid or empty, skip it
                if face.size == 0:
                    continue

                face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
                face = cv2.resize(face, (224, 224))
                face = np.array(face) / 255.0
                face = np.expand_dims(face, axis=0)
                
                (mask, withoutMask) = maskNet.predict(face, verbose=0)[0]

                label = "Mask" if mask > withoutMask else "No Mask"
                
                results.append({
                    "box": [int(startX), int(startY), int(endX), int(endY)],
                    "label": label,
                    "confidence": float(confidence)
                })
        return jsonify(results)

    except Exception as e:
        # If any other error happens during processing, log it and send back an error
        logging.error(f"Error during detection: {e}")
        return jsonify({"error": "An internal error occurred during image processing."}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)

