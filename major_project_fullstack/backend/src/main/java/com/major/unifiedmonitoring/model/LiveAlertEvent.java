package com.major.unifiedmonitoring.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.Lob;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;

import java.time.Instant;

@Entity
@Table(
        name = "live_alert_events",
        indexes = {
                @Index(name = "idx_live_alert_created_at", columnList = "createdAt"),
                @Index(name = "idx_live_alert_service", columnList = "serviceType"),
                @Index(name = "idx_live_alert_session", columnList = "sessionId")
        }
)
public class LiveAlertEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 128)
    private String sessionId;

    @Column(nullable = false, length = 64)
    private String serviceType;

    @Column(nullable = false, length = 32)
    private String status;

    @Column(nullable = false)
    private boolean alertTriggered;

    @Column(length = 32)
    private String severity;

    @Column(length = 500)
    private String message;

    private Double confidencePct;

    private Integer detections;

    @Lob
    private String payloadJson;

    @Column(nullable = false, updatable = false)
    private Instant createdAt;

    @PrePersist
    public void onCreate() {
        createdAt = Instant.now();
    }

    public Long getId() {
        return id;
    }

    public String getSessionId() {
        return sessionId;
    }

    public void setSessionId(String sessionId) {
        this.sessionId = sessionId;
    }

    public String getServiceType() {
        return serviceType;
    }

    public void setServiceType(String serviceType) {
        this.serviceType = serviceType;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public boolean isAlertTriggered() {
        return alertTriggered;
    }

    public void setAlertTriggered(boolean alertTriggered) {
        this.alertTriggered = alertTriggered;
    }

    public String getSeverity() {
        return severity;
    }

    public void setSeverity(String severity) {
        this.severity = severity;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public Double getConfidencePct() {
        return confidencePct;
    }

    public void setConfidencePct(Double confidencePct) {
        this.confidencePct = confidencePct;
    }

    public Integer getDetections() {
        return detections;
    }

    public void setDetections(Integer detections) {
        this.detections = detections;
    }

    public String getPayloadJson() {
        return payloadJson;
    }

    public void setPayloadJson(String payloadJson) {
        this.payloadJson = payloadJson;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }
}
