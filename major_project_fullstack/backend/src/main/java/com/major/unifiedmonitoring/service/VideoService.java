package com.major.unifiedmonitoring.service;

import com.major.unifiedmonitoring.dto.VideoResponse;
import com.major.unifiedmonitoring.model.User;
import com.major.unifiedmonitoring.model.VideoAsset;
import com.major.unifiedmonitoring.repository.UserRepository;
import com.major.unifiedmonitoring.repository.VideoAssetRepository;
import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

@Service
public class VideoService {

    @Value("${app.storage.video-root}")
    private String videoRoot;

    @Value("${app.integrations.workspace-root:/Users/saidharahasrao/Major}")
    private String workspaceRoot;

    @Value("${app.integrations.python-bin:python3}")
    private String pythonBin;

    private final VideoAssetRepository videoAssetRepository;
    private final UserRepository userRepository;
    private Path videoStoragePath;

    public VideoService(VideoAssetRepository videoAssetRepository, UserRepository userRepository) {
        this.videoAssetRepository = videoAssetRepository;
        this.userRepository = userRepository;
    }

    @PostConstruct
    public void ensureStorage() throws IOException {
        videoStoragePath = Paths.get(videoRoot).toAbsolutePath().normalize();
        Files.createDirectories(videoStoragePath);
    }

    public VideoResponse uploadVideo(Long userId, MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new IllegalArgumentException("Video file is empty.");
        }
        validateVideoExtension(file.getOriginalFilename());

        User user = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found"));

        String originalName = file.getOriginalFilename() == null ? "uploaded_video" : file.getOriginalFilename();
        String extension = getExtension(originalName);
        String storedName = UUID.randomUUID() + extension;

        Path destination = videoStoragePath.resolve(storedName);
        try {
            Files.copy(file.getInputStream(), destination, StandardCopyOption.REPLACE_EXISTING);
        } catch (IOException ex) {
            throw new IllegalStateException("Could not store video on disk", ex);
        }

        double durationSeconds = probeDurationSeconds(destination);

        VideoAsset asset = new VideoAsset();
        asset.setOriginalFilename(originalName);
        asset.setStoredFilename(storedName);
        asset.setFilePath(destination.toString());
        asset.setContentType(file.getContentType() == null ? "application/octet-stream" : file.getContentType());
        asset.setSizeBytes(file.getSize());
        asset.setDurationSeconds(Math.max(0.0, durationSeconds));
        asset.setUploadedBy(user);

        return toResponse(videoAssetRepository.save(asset));
    }

    public List<VideoResponse> getVideosForUser(Long userId) {
        return videoAssetRepository.findAllByUploadedByIdOrderByUploadedAtDesc(userId)
                .stream()
                .map(this::toResponse)
                .toList();
    }

    public VideoAsset getVideoForUserOrThrow(Long userId, Long videoId) {
        return videoAssetRepository.findByIdAndUploadedById(videoId, userId)
                .orElseThrow(() -> new IllegalArgumentException("Video not found for this user."));
    }

    private VideoResponse toResponse(VideoAsset asset) {
        VideoResponse response = new VideoResponse();
        response.setId(asset.getId());
        response.setOriginalFilename(asset.getOriginalFilename());
        response.setContentType(asset.getContentType());
        response.setSizeBytes(asset.getSizeBytes());
        response.setDurationSeconds(asset.getDurationSeconds());
        response.setStoragePath(asset.getFilePath());
        response.setUploadedAt(asset.getUploadedAt());
        return response;
    }

    private void validateVideoExtension(String originalFilename) {
        if (originalFilename == null || originalFilename.isBlank()) {
            throw new IllegalArgumentException("Video filename is missing.");
        }
        String extension = getExtension(originalFilename).toLowerCase();
        List<String> allowed = List.of(".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm");
        if (!allowed.contains(extension)) {
            throw new IllegalArgumentException("Unsupported video format. Allowed: mp4, mov, avi, mkv, m4v, webm.");
        }
    }

    private double probeDurationSeconds(Path videoPath) {
        double ffprobeDuration = probeDurationWithFfprobe(videoPath);
        if (ffprobeDuration > 0) {
            return ffprobeDuration;
        }
        return probeDurationWithPython(videoPath);
    }

    private double probeDurationWithFfprobe(Path videoPath) {
        ProcessBuilder processBuilder = new ProcessBuilder(
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                videoPath.toAbsolutePath().toString()
        );
        processBuilder.redirectErrorStream(true);
        try {
            Process process = processBuilder.start();
            boolean finished = process.waitFor(10, TimeUnit.SECONDS);
            if (!finished || process.exitValue() != 0) {
                return 0.0;
            }
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
                String line = reader.readLine();
                if (line == null || line.isBlank()) {
                    return 0.0;
                }
                return Math.max(0.0, Double.parseDouble(line.trim()));
            }
        } catch (Exception ignored) {
            return 0.0;
        }
    }

    private double probeDurationWithPython(Path videoPath) {
        Path workspace = Paths.get(workspaceRoot).toAbsolutePath().normalize();
        List<String> candidates = new ArrayList<>();
        candidates.add(workspace.resolve("Crowd-Gathering-Detection-main/venv/bin/python3").toString());
        candidates.add(workspace.resolve("intelligent_monitoring_system/ai_service/.venv/bin/python3").toString());
        candidates.add(workspace.resolve("intelligent_monitoring_system/ai_service/venv/bin/python3").toString());
        candidates.add(pythonBin);

        String script = "import cv2,sys;cap=cv2.VideoCapture(sys.argv[1]);"
                + "fps=cap.get(cv2.CAP_PROP_FPS) or 0;count=cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0;"
                + "cap.release();print((count/fps) if fps>0 and count>0 else 0)";

        for (String candidate : candidates) {
            try {
                if (!"python3".equals(candidate) && !candidate.equals(pythonBin) && !Files.exists(Paths.get(candidate))) {
                    continue;
                }
                ProcessBuilder pb = new ProcessBuilder(candidate, "-c", script, videoPath.toAbsolutePath().toString());
                pb.redirectErrorStream(true);
                Process process = pb.start();
                boolean finished = process.waitFor(10, TimeUnit.SECONDS);
                if (!finished || process.exitValue() != 0) {
                    continue;
                }
                try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
                    String line = reader.readLine();
                    if (line == null || line.isBlank()) {
                        continue;
                    }
                    double duration = Double.parseDouble(line.trim());
                    if (duration > 0) {
                        return duration;
                    }
                }
            } catch (Exception ignored) {
                // Try next Python runtime.
            }
        }
        return 0.0;
    }

    private String getExtension(String filename) {
        int idx = filename.lastIndexOf('.');
        if (idx == -1) {
            return ".mp4";
        }
        return filename.substring(idx);
    }
}
