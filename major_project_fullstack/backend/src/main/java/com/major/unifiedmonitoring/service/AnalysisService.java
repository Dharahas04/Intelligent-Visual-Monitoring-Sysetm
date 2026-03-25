package com.major.unifiedmonitoring.service;

import com.major.unifiedmonitoring.dto.AnalysisJobResponse;
import com.major.unifiedmonitoring.dto.RunAnalysisRequest;
import com.major.unifiedmonitoring.model.AiService;
import com.major.unifiedmonitoring.model.AnalysisJob;
import com.major.unifiedmonitoring.model.JobStatus;
import com.major.unifiedmonitoring.model.User;
import com.major.unifiedmonitoring.model.VideoAsset;
import com.major.unifiedmonitoring.repository.AnalysisJobRepository;
import com.major.unifiedmonitoring.repository.UserRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.task.TaskExecutor;
import org.springframework.stereotype.Service;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.TimeUnit;

@Service
public class AnalysisService {

    private static final int MAX_LOG_CHARS = 50000;

    @Value("${app.integrations.workspace-root}")
    private String workspaceRoot;

    @Value("${app.integrations.python-bin:python3}")
    private String pythonBin;

    @Value("${app.storage.result-root:../storage/results}")
    private String resultRoot;

    @Value("${app.storage.video-root:../storage/videos}")
    private String videoRoot;

    @Value("${app.integrations.job-timeout-seconds:3600}")
    private long jobTimeoutSeconds;

    private final AnalysisJobRepository analysisJobRepository;
    private final UserRepository userRepository;
    private final VideoService videoService;
    private final TaskExecutor taskExecutor;

    public AnalysisService(
            AnalysisJobRepository analysisJobRepository,
            UserRepository userRepository,
            VideoService videoService,
            TaskExecutor taskExecutor
    ) {
        this.analysisJobRepository = analysisJobRepository;
        this.userRepository = userRepository;
        this.videoService = videoService;
        this.taskExecutor = taskExecutor;
    }

    public AnalysisJobResponse submitJob(Long userId, RunAnalysisRequest request) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found."));
        VideoAsset video = videoService.getVideoForUserOrThrow(userId, request.getVideoId());

        AnalysisJob job = new AnalysisJob();
        job.setRequestedBy(user);
        job.setVideo(video);
        job.setServiceType(request.getServiceType());
        job.setStatus(JobStatus.QUEUED);

        AnalysisJob saved = analysisJobRepository.save(job);
        taskExecutor.execute(() -> runJob(saved.getId()));
        return toResponse(saved);
    }

    public List<AnalysisJobResponse> getJobs(Long userId) {
        return analysisJobRepository.findAllByRequestedByIdOrderByCreatedAtDesc(userId)
                .stream()
                .map(this::toResponse)
                .toList();
    }

    public AnalysisJobResponse getJob(Long userId, Long jobId) {
        AnalysisJob job = analysisJobRepository.findByIdAndRequestedById(jobId, userId)
                .orElseThrow(() -> new IllegalArgumentException("Analysis job not found for this user."));
        return toResponse(job);
    }

    public Path getJobOutputPathForUser(Long userId, Long jobId) {
        AnalysisJob job = analysisJobRepository.findByIdAndRequestedById(jobId, userId)
                .orElseThrow(() -> new IllegalArgumentException("Analysis job not found for this user."));

        if (job.getStatus() != JobStatus.COMPLETED) {
            throw new IllegalArgumentException("Analysis job is not completed yet.");
        }
        if (job.getOutputLocation() == null || job.getOutputLocation().isBlank()) {
            throw new IllegalStateException("Completed job has no output path.");
        }

        Path outputPath = Paths.get(job.getOutputLocation()).toAbsolutePath().normalize();
        if (!Files.exists(outputPath) || !Files.isReadable(outputPath)) {
            throw new IllegalStateException("Output file is missing or unreadable.");
        }
        return outputPath;
    }

    private void runJob(Long jobId) {
        AnalysisJob job = analysisJobRepository.findById(jobId)
                .orElseThrow(() -> new IllegalArgumentException("Job does not exist."));

        try {
            job.setStatus(JobStatus.RUNNING);
            job.setStartedAt(Instant.now());
            job.setCompletedAt(null);
            job.setErrorMessage(null);
            analysisJobRepository.save(job);

            CommandDefinition commandDefinition = buildCommand(job);
            validateInputVideo(commandDefinition.inputVideoPath(), job.getServiceType());

            job.setCommandExecuted(String.join(" ", commandDefinition.command()));
            analysisJobRepository.save(job);

            ProcessBuilder processBuilder = new ProcessBuilder(commandDefinition.command());
            processBuilder.directory(commandDefinition.workingDirectory().toFile());
            Process process = processBuilder.start();

            StringBuilder stdout = new StringBuilder();
            StringBuilder stderr = new StringBuilder();

            Thread stdoutThread = new Thread(() -> consumeStream(process.getInputStream(), stdout));
            Thread stderrThread = new Thread(() -> consumeStream(process.getErrorStream(), stderr));
            stdoutThread.start();
            stderrThread.start();

            boolean finished = process.waitFor(jobTimeoutSeconds, TimeUnit.SECONDS);
            if (!finished) {
                process.destroyForcibly();
                process.waitFor(5, TimeUnit.SECONDS);
            }

            joinThread(stdoutThread);
            joinThread(stderrThread);

            String stdoutText = stdout.toString();
            String stderrText = stderr.toString();
            job.setExecutionLog(formatExecutionLog(stdoutText, stderrText));
            job.setResultPayload(extractJsonPayload(stdoutText));
            job.setCompletedAt(Instant.now());
            job.setDurationSeconds(calculateDurationSeconds(job.getStartedAt(), job.getCompletedAt()));

            if (!finished) {
                job.setStatus(JobStatus.FAILED);
                job.setErrorMessage("Analysis timed out after " + jobTimeoutSeconds + " seconds.");
                analysisJobRepository.save(job);
                return;
            }

            int exitCode = process.exitValue();
            if (exitCode != 0) {
                job.setStatus(JobStatus.FAILED);
                job.setErrorMessage(buildProcessErrorMessage(exitCode, stdoutText, stderrText));
                analysisJobRepository.save(job);
                return;
            }

            Path outputPath = Paths.get(commandDefinition.outputLocation()).toAbsolutePath().normalize();
            if (!Files.exists(outputPath) || Files.size(outputPath) <= 0) {
                job.setStatus(JobStatus.FAILED);
                job.setErrorMessage("Model process ended but output file was not generated.");
                analysisJobRepository.save(job);
                return;
            }

            job.setStatus(JobStatus.COMPLETED);
            job.setOutputLocation(outputPath.toString());
            analysisJobRepository.save(job);
        } catch (Exception ex) {
            job.setStatus(JobStatus.FAILED);
            job.setCompletedAt(Instant.now());
            job.setDurationSeconds(calculateDurationSeconds(job.getStartedAt(), job.getCompletedAt()));
            job.setErrorMessage(extractRootMessage(ex));
            analysisJobRepository.save(job);
        }
    }

    private void consumeStream(InputStream stream, StringBuilder target) {
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(stream))) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (target.length() < MAX_LOG_CHARS) {
                    target.append(line).append(System.lineSeparator());
                }
            }
        } catch (IOException ignored) {
            // Stream read errors should not crash the job lifecycle.
        }
    }

    private void joinThread(Thread thread) {
        try {
            thread.join(10000);
        } catch (InterruptedException ignored) {
            Thread.currentThread().interrupt();
        }
    }

    private String formatExecutionLog(String stdout, String stderr) {
        return "[STDOUT]" + System.lineSeparator()
                + Optional.ofNullable(stdout).orElse("")
                + System.lineSeparator()
                + "[STDERR]"
                + System.lineSeparator()
                + Optional.ofNullable(stderr).orElse("");
    }

    private String buildProcessErrorMessage(int exitCode, String stdout, String stderr) {
        String errorTail = tailNonEmpty(stderr, 8);
        if (errorTail.isBlank()) {
            errorTail = tailNonEmpty(stdout, 8);
        }
        if (errorTail.isBlank()) {
            return "Execution failed with exit code " + exitCode + ".";
        }
        return "Execution failed with exit code " + exitCode + ": " + errorTail;
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

    private String extractJsonPayload(String stdout) {
        if (stdout == null || stdout.isBlank()) {
            return null;
        }
        String[] lines = stdout.split("\\R");
        for (int i = lines.length - 1; i >= 0; i--) {
            String line = lines[i].trim();
            if (line.startsWith("{") && line.endsWith("}")) {
                return line;
            }
        }
        return null;
    }

    private String extractRootMessage(Exception ex) {
        Throwable cursor = ex;
        while (cursor.getCause() != null) {
            cursor = cursor.getCause();
        }
        return cursor.getMessage() == null ? ex.getClass().getSimpleName() : cursor.getMessage();
    }

    private Double calculateDurationSeconds(Instant startedAt, Instant completedAt) {
        if (startedAt == null || completedAt == null) {
            return null;
        }
        return Duration.between(startedAt, completedAt).toMillis() / 1000.0;
    }

    private void validateInputVideo(String inputVideoPath, AiService serviceType) {
        Path videoPath = Paths.get(inputVideoPath).toAbsolutePath().normalize();
        if (!Files.exists(videoPath)) {
            throw new IllegalStateException("Input video does not exist: " + videoPath);
        }
        if (!Files.isReadable(videoPath)) {
            throw new IllegalStateException("Input video is not readable: " + videoPath);
        }

        try {
            long bytes = Files.size(videoPath);
            if (bytes <= 1024) {
                throw new IllegalArgumentException("Input video file is too small/corrupt.");
            }
        } catch (IOException ex) {
            throw new IllegalStateException("Unable to read input video metadata.", ex);
        }

        double duration = probeVideoDurationSeconds(videoPath);
        if (duration > 0 && duration < 0.5) {
            throw new IllegalArgumentException("Input video duration is too short for analysis.");
        }

        if (serviceType == AiService.ANPR && duration > 0 && duration < 1.5) {
            // ANPR can run on short clips, but warning-level threshold prevents unstable frame extraction.
            throw new IllegalArgumentException("ANPR requires slightly longer clips. Please upload a video of at least 1.5 seconds.");
        }
    }

    private double probeVideoDurationSeconds(Path videoPath) {
        ProcessBuilder pb = new ProcessBuilder(
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                videoPath.toAbsolutePath().toString()
        );
        pb.redirectErrorStream(true);
        try {
            Process process = pb.start();
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

    private CommandDefinition buildCommand(AnalysisJob job) {
        Path workspace = Paths.get(workspaceRoot).toAbsolutePath().normalize();
        Path resultsDirectory = Paths.get(resultRoot).toAbsolutePath().normalize();
        ensureDirectoryExists(resultsDirectory, "Results storage path is not writable.");

        AiService serviceType = job.getServiceType();
        String inputVideoPath = resolveInputVideoPath(job.getVideo().getFilePath(), workspace);

        return switch (serviceType) {
            case ANPR -> {
                Path connectorRoot = workspace.resolve("major_project_fullstack/connectors");
                Path anprRoot = workspace.resolve("Automatic-Number-Plate-Recognition-using-YOLOv5");
                Path crowdGatheringRoot = workspace.resolve("Crowd-Gathering-Detection-main");
                String python = resolvePythonWithImports(
                        List.of(
                                anprRoot.resolve("venv/bin/python3"),
                                anprRoot.resolve("venv/bin/python"),
                                crowdGatheringRoot.resolve("venv/bin/python3"),
                                crowdGatheringRoot.resolve("venv/bin/python")
                        ),
                        List.of("cv2", "ultralytics", "numpy", "torch")
                );

                Path weightsPath = anprRoot.resolve("Weights/best.pt");
                Path outputPath = resultsDirectory.resolve("anpr_job_" + job.getId() + ".mp4");
                ensureExists(connectorRoot.resolve("run_anpr.py"), "ANPR connector script not found.");
                ensureExists(weightsPath, "ANPR weights file not found.");

                List<String> command = List.of(
                        python,
                        "run_anpr.py",
                        "--weights",
                        weightsPath.toString(),
                        "--source",
                        inputVideoPath,
                        "--output",
                        outputPath.toString()
                );
                yield new CommandDefinition(connectorRoot, command, outputPath.toString(), inputVideoPath);
            }
            case CROWD_ANOMALY -> {
                Path serviceRoot = workspace.resolve("Crowd-Anomaly-Detection-master");
                String python = resolvePythonExecutable(
                        List.of(
                                serviceRoot.resolve("venv/bin/python3"),
                                serviceRoot.resolve("venv/bin/python"),
                                serviceRoot.resolve(".venv/bin/python3"),
                                serviceRoot.resolve(".venv/bin/python")
                        )
                );

                Path outputPath = resultsDirectory.resolve("anomaly_output_job_" + job.getId() + ".mp4");
                Path trainScores = serviceRoot.resolve("train_scores.npy");
                ensureExists(serviceRoot.resolve("load_predict.py"), "Crowd anomaly script not found.");

                List<String> command = new ArrayList<>();
                command.add(python);
                command.add("load_predict.py");
                command.add("--video");
                command.add(inputVideoPath);
                command.add("--output");
                command.add(outputPath.toString());
                if (Files.exists(trainScores)) {
                    command.add("--train-scores");
                    command.add(trainScores.toString());
                }

                yield new CommandDefinition(serviceRoot, command, outputPath.toString(), inputVideoPath);
            }
            case CROWD_GATHERING -> {
                Path serviceRoot = workspace.resolve("Crowd-Gathering-Detection-main");
                String servicePython = resolvePythonWithImports(
                        List.of(
                                serviceRoot.resolve("venv/bin/python3"),
                                serviceRoot.resolve("venv/bin/python")
                        ),
                        List.of("cv2", "numpy", "ultralytics")
                );
                Path outputPath = resultsDirectory.resolve("crowd_gathering_job_" + job.getId() + ".mp4");
                Path serviceScript = serviceRoot.resolve("crowd_gathering.py");
                boolean canRunPrimary = Files.exists(serviceScript)
                        && canImportModules(servicePython, List.of("cv2", "numpy", "ultralytics"));

                if (canRunPrimary) {
                    List<String> command = List.of(
                            servicePython,
                            "crowd_gathering.py",
                            "--video",
                            inputVideoPath,
                            "--output",
                            outputPath.toString()
                    );
                    yield new CommandDefinition(serviceRoot, command, outputPath.toString(), inputVideoPath);
                }

                Path connectorRoot = workspace.resolve("major_project_fullstack/connectors");
                String connectorPython = resolvePythonWithImports(List.of(), List.of("cv2", "numpy"));
                ensureExists(connectorRoot.resolve("run_crowd_gathering.py"), "Crowd gathering connector script not found.");

                List<String> command = List.of(
                        connectorPython,
                        "run_crowd_gathering.py",
                        "--video",
                        inputVideoPath,
                        "--output",
                        outputPath.toString()
                );
                yield new CommandDefinition(connectorRoot, command, outputPath.toString(), inputVideoPath);
            }
            case MASK_DETECTION -> {
                Path serviceRoot = workspace.resolve("intelligent_monitoring_system/ai_service");
                String servicePython = resolvePythonWithImports(
                        List.of(
                                serviceRoot.resolve(".venv/bin/python3"),
                                serviceRoot.resolve(".venv/bin/python"),
                                serviceRoot.resolve("venv/bin/python3"),
                                serviceRoot.resolve("venv/bin/python")
                        ),
                        List.of("cv2", "numpy", "tensorflow")
                );
                Path outputPath = resultsDirectory.resolve("mask_detection_job_" + job.getId() + ".mp4");
                Path primaryScript = serviceRoot.resolve("mask_detector_final.py");
                boolean canRunPrimary = Files.exists(primaryScript)
                        && canImportModules(servicePython, List.of("cv2", "numpy", "tensorflow"));

                if (canRunPrimary) {
                    List<String> command = List.of(
                            servicePython,
                            "mask_detector_final.py",
                            "--video",
                            inputVideoPath,
                            "--output",
                            outputPath.toString(),
                            "--no-display"
                    );
                    yield new CommandDefinition(serviceRoot, command, outputPath.toString(), inputVideoPath);
                }

                Path connectorRoot = workspace.resolve("major_project_fullstack/connectors");
                String connectorPython = resolvePythonWithImports(List.of(), List.of("cv2", "numpy"));
                ensureExists(connectorRoot.resolve("run_mask_detection.py"), "Mask detection connector script not found.");

                List<String> command = List.of(
                        connectorPython,
                        "run_mask_detection.py",
                        "--video",
                        inputVideoPath,
                        "--output",
                        outputPath.toString()
                );
                yield new CommandDefinition(connectorRoot, command, outputPath.toString(), inputVideoPath);
            }
        };
    }

    private AnalysisJobResponse toResponse(AnalysisJob job) {
        AnalysisJobResponse response = new AnalysisJobResponse();
        response.setId(job.getId());
        response.setServiceType(job.getServiceType().name());
        response.setStatus(job.getStatus());
        response.setVideoName(job.getVideo().getOriginalFilename());
        response.setOutputLocation(job.getOutputLocation());
        response.setErrorMessage(job.getErrorMessage());
        response.setDurationSeconds(job.getDurationSeconds());
        response.setResultPayload(job.getResultPayload());
        response.setCreatedAt(job.getCreatedAt());
        response.setStartedAt(job.getStartedAt());
        response.setCompletedAt(job.getCompletedAt());
        return response;
    }

    private void ensureExists(Path path, String message) {
        if (!Files.exists(path)) {
            throw new IllegalStateException(message);
        }
    }

    private void ensureDirectoryExists(Path path, String message) {
        try {
            Files.createDirectories(path);
        } catch (IOException ex) {
            throw new IllegalStateException(message, ex);
        }
    }

    private String resolvePythonExecutable(List<Path> candidates) {
        for (Path candidate : candidates) {
            if (Files.exists(candidate)) {
                return candidate.toAbsolutePath().toString();
            }
        }
        return pythonBin;
    }

    private String resolvePythonWithImports(List<Path> candidates, List<String> imports) {
        for (Path candidate : candidates) {
            if (!Files.exists(candidate)) {
                continue;
            }
            String abs = candidate.toAbsolutePath().toString();
            if (canImportModules(abs, imports)) {
                return abs;
            }
        }
        return resolvePythonExecutable(candidates);
    }

    private boolean canImportModules(String pythonExecutable, List<String> imports) {
        String importStatement = "import " + String.join(",", imports);
        ProcessBuilder pb = new ProcessBuilder(pythonExecutable, "-c", importStatement);
        pb.redirectErrorStream(true);
        try {
            Process process = pb.start();
            boolean finished = process.waitFor(15, TimeUnit.SECONDS);
            return finished && process.exitValue() == 0;
        } catch (Exception ignored) {
            return false;
        }
    }

    private String resolveInputVideoPath(String storedPath, Path workspace) {
        if (storedPath == null || storedPath.isBlank()) {
            return storedPath;
        }

        Path direct = Paths.get(storedPath);
        if (Files.exists(direct)) {
            return direct.toAbsolutePath().toString();
        }

        Path fileName = direct.getFileName();
        List<Path> candidates = new ArrayList<>();

        if (fileName != null) {
            Path configuredVideoRoot = Paths.get(videoRoot).toAbsolutePath().normalize();
            candidates.add(configuredVideoRoot.resolve(fileName));
            candidates.add(workspace.resolve("major_project_fullstack/storage/videos").resolve(fileName));
        }

        String normalized = storedPath.replace('\\', '/');
        String marker = "/storage/videos/";
        int markerIndex = normalized.indexOf(marker);
        if (markerIndex >= 0) {
            String relative = normalized.substring(markerIndex + marker.length()).trim();
            if (!relative.isBlank()) {
                Path configuredVideoRoot = Paths.get(videoRoot).toAbsolutePath().normalize();
                candidates.add(configuredVideoRoot.resolve(relative).normalize());
                candidates.add(workspace.resolve("major_project_fullstack/storage/videos").resolve(relative).normalize());
            }
        }

        for (Path candidate : candidates) {
            if (Files.exists(candidate) && Files.isRegularFile(candidate)) {
                return candidate.toAbsolutePath().toString();
            }
        }

        return direct.toAbsolutePath().toString();
    }

    private record CommandDefinition(Path workingDirectory, List<String> command, String outputLocation, String inputVideoPath) {
    }
}
