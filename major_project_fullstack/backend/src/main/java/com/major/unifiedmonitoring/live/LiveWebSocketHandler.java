package com.major.unifiedmonitoring.live;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.major.unifiedmonitoring.service.LiveMonitoringService;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.io.IOException;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;

@Component
public class LiveWebSocketHandler extends TextWebSocketHandler {

    private final ObjectMapper objectMapper;
    private final LiveMonitoringService liveMonitoringService;

    public LiveWebSocketHandler(ObjectMapper objectMapper, LiveMonitoringService liveMonitoringService) {
        this.objectMapper = objectMapper;
        this.liveMonitoringService = liveMonitoringService;
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        session.setTextMessageSizeLimit(4 * 1024 * 1024);
        session.setBinaryMessageSizeLimit(4 * 1024 * 1024);
        liveMonitoringService.registerSession(session.getId(), payload -> sendSafely(session, payload));
        sendSystem(session, "info", "Live channel connected.");
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) {
        try {
            LiveFrameMessage payload = objectMapper.readValue(message.getPayload(), LiveFrameMessage.class);
            String type = payload.getType() == null ? "frame" : payload.getType().trim().toLowerCase();

            if ("ping".equals(type)) {
                sendJson(session, Map.of("type", "pong", "serverTs", Instant.now().toString()));
                return;
            }

            if (!"frame".equals(type)) {
                sendSystem(session, "warning", "Unsupported live message type.");
                return;
            }

            boolean accepted = liveMonitoringService.enqueueFrame(session.getId(), payload);
            sendJson(session, Map.of(
                    "type", accepted ? "queued" : "dropped",
                    "serviceType", payload.getServiceType(),
                    "serverTs", Instant.now().toString()
            ));
        } catch (Exception ex) {
            sendSystem(session, "error", "Invalid live payload: " + shortText(ex.getMessage()));
        }
    }

    @Override
    public void handleTransportError(WebSocketSession session, Throwable exception) {
        sendSystem(session, "error", "Live transport error: " + shortText(exception.getMessage()));
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        liveMonitoringService.unregisterSession(session.getId());
    }

    private void sendSystem(WebSocketSession session, String level, String message) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("type", "system");
        payload.put("level", level);
        payload.put("message", message);
        payload.put("serverTs", Instant.now().toString());
        sendJson(session, payload);
    }

    private void sendJson(WebSocketSession session, Map<String, ?> payload) {
        try {
            sendSafely(session, objectMapper.writeValueAsString(payload));
        } catch (Exception ignored) {
            // Ignore message serialization/send failures.
        }
    }

    private void sendSafely(WebSocketSession session, String payload) {
        if (session == null || !session.isOpen()) {
            return;
        }
        synchronized (session) {
            try {
                session.sendMessage(new TextMessage(payload));
            } catch (IOException ignored) {
                // Ignore transient socket write errors.
            }
        }
    }

    private String shortText(String text) {
        if (text == null || text.isBlank()) {
            return "unknown error";
        }
        String compact = text.replaceAll("\\s+", " ").trim();
        if (compact.length() <= 160) {
            return compact;
        }
        return compact.substring(0, 159) + "…";
    }
}
