package com.major.unifiedmonitoring.model;

public enum AiService {
    ANPR("Automatic Number Plate Recognition", "YOLO-based number plate detection on uploaded videos."),
    CROWD_ANOMALY("Crowd Anomaly Detection", "Detects unusual crowd motion and suspicious activity."),
    CROWD_GATHERING("Crowd Gathering Detection", "Detects dense gatherings and crowd line-cross events."),
    MASK_DETECTION("Mask Compliance Detection", "Detects mask and no-mask faces in media streams.");

    private final String title;
    private final String description;

    AiService(String title, String description) {
        this.title = title;
        this.description = description;
    }

    public String getTitle() {
        return title;
    }

    public String getDescription() {
        return description;
    }
}
