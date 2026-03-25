package com.major.unifiedmonitoring.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.major.unifiedmonitoring.live.LiveFrameMessage;
import com.major.unifiedmonitoring.model.LiveAlertEvent;
import com.major.unifiedmonitoring.repository.LiveAlertEventRepository;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.Consumer;

@Service
public class LiveMonitoringService {

    private static final int MAX_FRAME_BYTES = 4_000_000;
    private static final int MAX_LOG_TAIL = 250;

    @Value("${app.integrations.workspace-root}")
    private String workspaceRoot;

    @Value("${app.integrations.python-bin:python3}")
    private String pythonBin;

    @Value("${app.live.redis-enabled:true}")
    private boolean redisEnabled;

    @Value("${app.live.redis-queue-key:intelmon:live:frames}")
    private String redisQueueKey;

    @Value("${app.live.max-queue-depth:250}")
    private int maxQueueDepth;

    @Value("${app.live.min-frame-interval-ms:300}")
    private long minFrameIntervalMs;

    @Value("${app.live.inference-timeout-seconds:20}")
    private long inferenceTimeoutSeconds;

    private final ObjectMapper objectMapper;
    private final StringRedisTemplate redisTemplate;
    private final LiveAlertEventRepository liveAlertEventRepository;
    private final BlockingQueue<LiveFrameTask> localQueue = new LinkedBlockingQueue<>();
    private final Map<String, Consumer<String>> sessionEmitters = new ConcurrentHashMap<>();
    private final Map<String, Long> lastFrameBySession = new ConcurrentHashMap<>();
    private final AtomicBoolean running = new AtomicBoolean(true);

    private ExecutorService workerExecutor;
    private volatile String pythonExecutable;
    private volatile Path liveScriptPath;
    private volatile String queueMode = "LOCAL";
    private volatile String lastQueueError = "";

    public LiveMonitoringService(
            ObjectMapper objectMapper,
            ObjectProvider<StringRedisTemplate> redisProvider,
            LiveAlertEventRepository liveAlertEventRepository
    ) {
        this.objectMapper = objectMapper;
        this.redisTemplate = redisProvider.getIfAvailable();
        this.liveAlertEventRepository = liveAlertEventRepository;
    }

    @PostConstruct
    public void init() {
        this.liveScriptPath = Paths.get(workspaceRoot)
                .toAbsolutePath()
                .normalize()
                .resolve("major_project_fullstack/connectors/live_frame_infer.py");
        this.pythonExecutable = resolvePythonExecutable();

        workerExecutor = Executors.newSingleThreadExecutor(r -> {
            Thread t = new Thread(r);
            t.setName("intelmon-live-worker");
            t.setDaemon(true);
            return t;
        });
        workerExecutor.submit(this::workerLoop);
    }

    @PreDestroy
    public void shutdown() {
        running.set(false);
        if (workerExecutor != null) {
            workerExecutor.shutdownNow();
        }
    }

    public void registerSession(String sessionId, Consumer<String> emitter) {
        sessionEmitters.put(sessionId, emitter);
    }

    public void unregisterSession(String sessionId) {
        sessionEmitters.remove(sessionId);
        lastFrameBySession.remove(sessionId);
    }

    public boolean enqueueFrame(String sessionId, LiveFrameMessage message) {
        if (message == null || message.getFrameData() == null || message.getFrameData().isBlank()) {
            return false;
        }

        String frameData = message.getFrameData().trim();
        if (frameData.length() > MAX_FRAME_BYTES) {
            publishSystem(sessionId, "error", "Frame payload too large.");
            return false;
        }

        long now = System.currentTimeMillis();
        Long last = lastFrameBySession.get(sessionId);
        if (last != null && (now - last) < minFrameIntervalMs) {
            return false;
        }
        lastFrameBySession.put(sessionId, now);

        String serviceType = normalizeService(message.getServiceType());
        LiveFrameTask task = new LiveFrameTask(sessionId, serviceType, frameData, now, message.getClientTs());

        int depth = getQueueDepth();
        if (depth >= maxQueueDepth) {
            publishSystem(sessionId, "warning", "Live queue is full. Slow down frame rate.");
            return false;
        }

        if (redisEnabled && redisTemplate != null) {
            try {
                redisTemplate.opsForList().rightPush(redisQueueKey, objectMapper.writeValueAsString(task));
                queueMode = "REDIS";
                return true;
            } catch (Exception ex) {
                lastQueueError = shortText(ex.getMessage());
            }
        }

        queueMode = "LOCAL";
        return localQueue.offer(task);
    }

    public Map<String, Object> statusSnapshot() {
        Map<String, Object> status = new LinkedHashMap<>();
        status.put("activeSessions", sessionEmitters.size());
        status.put("queueDepth", getQueueDepth());
        status.put("queueMode", queueMode);
        status.put("redisEnabled", redisEnabled);
        status.put("redisAvailable", redisTemplate != null);
        status.put("pythonExecutable", pythonExecutable);
        status.put("liveScript", liveScriptPath == null ? "" : liveScriptPath.toString());
        status.put("liveScriptPresent", liveScriptPath != null && Files.exists(liveScriptPath));
        status.put("lastQueueError", lastQueueError);
        status.put("recentAlerts", Math.min(100, recentAlerts(10).size()));
        status.put("timestamp", Instant.now().toString());
        return status;
    }

    public List<Map<String, Object>> recentAlerts(int limit) {
        int boundedLimit = Math.max(1, Math.min(100, limit));
        return liveAlertEventRepository.findTop100ByOrderByCreatedAtDesc()
                .stream()
                .sorted(Comparator.comparing(LiveAlertEvent::getCreatedAt).reversed())
                .limit(boundedLimit)
                .map(this::toAlertMap)
                .toList();
    }

    private void workerLoop() {
        while (running.get()) {
            try {
                LiveFrameTask task = pollTask();
                if (task == null) {
                    continue;
                }
                processTask(task);
            } catch (Exception ignored) {
                // Keep worker alive for continuous stream processing.
            }
        }
    }

    private LiveFrameTask pollTask() throws InterruptedException {
        if (redisEnabled && redisTemplate != null) {
            try {
                String payload = redisTemplate.opsForList().leftPop(redisQueueKey, Duration.ofMillis(250));
                if (payload != null && !payload.isBlank()) {
                    queueMode = "REDIS";
                    return objectMapper.readValue(payload, LiveFrameTask.class);
                }
            } catch (Exception ex) {
                lastQueueError = shortText(ex.getMessage());
            }
        }

        queueMode = "LOCAL";
        return localQueue.poll(300, TimeUnit.MILLISECONDS);
    }

    private void processTask(LiveFrameTask task) {
        long started = System.currentTimeMillis();
        Map<String, Object> result = runInference(task);
        long ended = System.currentTimeMillis();

        result.put("type", "result");
        result.put("sessionId", task.getSessionId());
        result.put("serviceType", task.getServiceType());
        result.put("processingMs", ended - started);
        result.put("queueDepth", getQueueDepth());
        result.put("serverTs", Instant.now().toString());

        persistAndNotifyIfAlert(task, result);
        publishResult(task.getSessionId(), result);
    }

    private Map<String, Object> runInference(LiveFrameTask task) {
        if (pythonExecutable == null || pythonExecutable.isBlank()) {
            return errorResult("Python runtime not available for live inference.");
        }
        if (liveScriptPath == null || !Files.exists(liveScriptPath)) {
            return errorResult("Live inference script is missing.");
        }

        List<String> command = new ArrayList<>();
        command.add(pythonExecutable);
        command.add(liveScriptPath.toString());
        command.add("--service");
        command.add(task.getServiceType());

        ProcessBuilder processBuilder = new ProcessBuilder(command);
        processBuilder.directory(liveScriptPath.getParent().toFile());

        try {
            Process process = processBuilder.start();
            try (OutputStream stdin = process.getOutputStream()) {
                stdin.write(task.getFrameData().getBytes(StandardCharsets.UTF_8));
                stdin.flush();
            }

            StringBuilder stdout = new StringBuilder();
            StringBuilder stderr = new StringBuilder();
            Thread stdoutThread = new Thread(() -> readStream(process.getInputStream(), stdout));
            Thread stderrThread = new Thread(() -> readStream(process.getErrorStream(), stderr));
            stdoutThread.start();
            stderrThread.start();

            boolean finished = process.waitFor(inferenceTimeoutSeconds, TimeUnit.SECONDS);
            if (!finished) {
                process.destroyForcibly();
                process.waitFor(3, TimeUnit.SECONDS);
            }

            stdoutThread.join(1000);
            stderrThread.join(1000);

            if (!finished) {
                return errorResult("Live inference timeout after " + inferenceTimeoutSeconds + "s.");
            }

            int exitCode = process.exitValue();
            if (exitCode != 0) {
                String reason = tailNonEmpty(stderr.toString(), 4);
                if (reason.isBlank()) {
                    reason = tailNonEmpty(stdout.toString(), 4);
                }
                if (reason.isBlank()) {
                    reason = "Inference process exited with code " + exitCode;
                }
                return errorResult(reason);
            }

            String jsonLine = extractJsonLine(stdout.toString());
            if (jsonLine == null) {
                return errorResult("Live inference returned no JSON payload.");
            }

            @SuppressWarnings("unchecked")
            Map<String, Object> payload = objectMapper.readValue(jsonLine, Map.class);
            payload.putIfAbsent("status", "COMPLETED");
            return payload;
        } catch (Exception ex) {
            return errorResult(shortText(ex.getMessage()));
        }
    }

    private void readStream(InputStream stream, StringBuilder target) {
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(stream))) {
            String line;
            while ((line = reader.readLine()) != null) {
                target.append(line).append('\n');
            }
        } catch (IOException ignored) {
            // Ignore stream read interruptions.
        }
    }

    private String extractJsonLine(String text) {
        if (text == null || text.isBlank()) {
            return null;
        }
        String[] lines = text.split("\\R");
        for (int i = lines.length - 1; i >= 0; i--) {
            String line = lines[i].trim();
            if (line.startsWith("{") && line.endsWith("}")) {
                return line;
            }
        }
        return null;
    }

    private void publishResult(String sessionId, Map<String, Object> payload) {
        Consumer<String> emitter = sessionEmitters.get(sessionId);
        if (emitter == null) {
            return;
        }
        try {
            emitter.accept(objectMapper.writeValueAsString(payload));
        } catch (JsonProcessingException ignored) {
            // Ignore serialization errors for non-critical live channel.
        }
    }

    private void publishSystem(String sessionId, String level, String message) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("type", "system");
        payload.put("level", level);
        payload.put("message", message);
        payload.put("serverTs", Instant.now().toString());
        publishResult(sessionId, payload);
    }

    private void persistAndNotifyIfAlert(LiveFrameTask task, Map<String, Object> result) {
        String status = stringValue(result.get("status"), "COMPLETED");
        boolean failed = "FAILED".equalsIgnoreCase(status);
        boolean alert = booleanValue(result.get("alert"));
        int noMaskDetections = intValue(result.get("noMaskDetections"), 0);

        if ("MASK_DETECTION".equalsIgnoreCase(task.getServiceType()) && noMaskDetections > 0) {
            alert = true;
        }

        if (!alert && !failed) {
            return;
        }

        String message = stringValue(result.get("message"), "");
        if (message.isBlank()) {
            message = failed
                    ? stringValue(result.get("error"), "Live inference failed")
                    : "Live alert detected";
        }

        String severity;
        if (failed) {
            severity = "ERROR";
        } else if ("MASK_DETECTION".equalsIgnoreCase(task.getServiceType()) && noMaskDetections > 0) {
            severity = "CRITICAL";
        } else {
            severity = "WARNING";
        }

        LiveAlertEvent event = new LiveAlertEvent();
        event.setSessionId(task.getSessionId());
        event.setServiceType(task.getServiceType());
        event.setStatus(status.toUpperCase());
        event.setAlertTriggered(alert);
        event.setSeverity(severity);
        event.setMessage(shortText(message));
        event.setConfidencePct(doubleValue(result.get("confidencePct")));
        event.setDetections(intValue(result.get("detections"), 0));
        event.setPayloadJson(toJson(result));
        liveAlertEventRepository.save(event);

        String systemLevel = failed ? "error" : "warning";
        String systemMessage = "MASK_DETECTION".equalsIgnoreCase(task.getServiceType()) && noMaskDetections > 0
                ? "No-mask alert triggered. " + shortText(message)
                : shortText(message);
        publishSystem(task.getSessionId(), systemLevel, systemMessage);
    }

    private Map<String, Object> toAlertMap(LiveAlertEvent event) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("id", event.getId());
        payload.put("sessionId", event.getSessionId());
        payload.put("serviceType", event.getServiceType());
        payload.put("status", event.getStatus());
        payload.put("alertTriggered", event.isAlertTriggered());
        payload.put("severity", event.getSeverity());
        payload.put("message", event.getMessage());
        payload.put("confidencePct", event.getConfidencePct());
        payload.put("detections", event.getDetections());
        payload.put("createdAt", event.getCreatedAt() == null ? null : event.getCreatedAt().toString());
        return payload;
    }

    private String toJson(Map<String, Object> payload) {
        try {
            return objectMapper.writeValueAsString(payload);
        } catch (JsonProcessingException ex) {
            return "{\"error\":\"payload_serialize_failed\"}";
        }
    }

    private String normalizeService(String raw) {
        if (raw == null || raw.isBlank()) {
            return "ANPR";
        }
        String value = raw.trim().toUpperCase();
        if ("CROWD".equals(value)) {
            return "CROWD_GATHERING";
        }
        return value;
    }

    private int getQueueDepth() {
        if (redisEnabled && redisTemplate != null) {
            try {
                Long size = redisTemplate.opsForList().size(redisQueueKey);
                if (size != null) {
                    return Math.toIntExact(Math.min(Integer.MAX_VALUE, size));
                }
            } catch (Exception ex) {
                lastQueueError = shortText(ex.getMessage());
            }
        }
        return localQueue.size();
    }

    private Map<String, Object> errorResult(String message) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("status", "FAILED");
        payload.put("error", Optional.ofNullable(message).orElse("Live inference error"));
        return payload;
    }

    private boolean booleanValue(Object value) {
        if (value instanceof Boolean bool) {
            return bool;
        }
        return value != null && "true".equalsIgnoreCase(String.valueOf(value));
    }

    private int intValue(Object value, int fallback) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        try {
            return value == null ? fallback : Integer.parseInt(String.valueOf(value));
        } catch (Exception ignored) {
            return fallback;
        }
    }

    private Double doubleValue(Object value) {
        if (value instanceof Number number) {
            return number.doubleValue();
        }
        try {
            return value == null ? null : Double.parseDouble(String.valueOf(value));
        } catch (Exception ignored) {
            return null;
        }
    }

    private String stringValue(Object value, String fallback) {
        String text = value == null ? "" : String.valueOf(value).trim();
        return text.isBlank() ? fallback : text;
    }

    private String shortText(String message) {
        String text = Objects.toString(message, "").replaceAll("\\s+", " ").trim();
        if (text.length() <= MAX_LOG_TAIL) {
            return text;
        }
        return text.substring(0, MAX_LOG_TAIL - 1) + "…";
    }

    private String tailNonEmpty(String text, int lines) {
        if (text == null || text.isBlank()) {
            return "";
        }
        String[] chunks = text.split("\\R");
        StringBuilder sb = new StringBuilder();
        int added = 0;
        for (int i = chunks.length - 1; i >= 0 && added < lines; i--) {
            String line = chunks[i].trim();
            if (line.isBlank()) {
                continue;
            }
            if (sb.length() > 0) {
                sb.insert(0, " | ");
            }
            sb.insert(0, line);
            added++;
        }
        return sb.toString();
    }

    private String resolvePythonExecutable() {
        Path workspace = Paths.get(workspaceRoot).toAbsolutePath().normalize();
        List<Path> candidates = List.of(
                workspace.resolve("Crowd-Gathering-Detection-main/venv/bin/python3"),
                workspace.resolve("Crowd-Anomaly-Detection-master/venv/bin/python3"),
                workspace.resolve("intelligent_monitoring_system/ai_service/.venv/bin/python3"),
                workspace.resolve("Automatic-Number-Plate-Recognition-using-YOLOv5/venv/bin/python3")
        );

        for (Path candidate : candidates) {
            if (!Files.exists(candidate)) {
                continue;
            }
            String executable = candidate.toAbsolutePath().toString();
            if (canImport(executable, List.of("cv2", "numpy"))) {
                return executable;
            }
        }

        if (canImport(pythonBin, List.of("cv2", "numpy"))) {
            return pythonBin;
        }
        return null;
    }

    private boolean canImport(String pythonExecutable, List<String> modules) {
        if (pythonExecutable == null || pythonExecutable.isBlank()) {
            return false;
        }
        String script = "import " + String.join(",", modules);
        ProcessBuilder pb = new ProcessBuilder(pythonExecutable, "-c", script);
        try {
            Process process = pb.start();
            boolean finished = process.waitFor(8, TimeUnit.SECONDS);
            return finished && process.exitValue() == 0;
        } catch (Exception ignored) {
            return false;
        }
    }

    private static class LiveFrameTask {
        private String sessionId;
        private String serviceType;
        private String frameData;
        private Long serverTs;
        private Long clientTs;

        public LiveFrameTask() {
        }

        public LiveFrameTask(String sessionId, String serviceType, String frameData, Long serverTs, Long clientTs) {
            this.sessionId = sessionId;
            this.serviceType = serviceType;
            this.frameData = frameData;
            this.serverTs = serverTs;
            this.clientTs = clientTs;
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

        public String getFrameData() {
            return frameData;
        }

        public void setFrameData(String frameData) {
            this.frameData = frameData;
        }

        public Long getServerTs() {
            return serverTs;
        }

        public void setServerTs(Long serverTs) {
            this.serverTs = serverTs;
        }

        public Long getClientTs() {
            return clientTs;
        }

        public void setClientTs(Long clientTs) {
            this.clientTs = clientTs;
        }
    }
}
