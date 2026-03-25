package com.major.unifiedmonitoring.controller;

import com.major.unifiedmonitoring.dto.AnalysisJobResponse;
import com.major.unifiedmonitoring.dto.RunAnalysisRequest;
import com.major.unifiedmonitoring.model.User;
import com.major.unifiedmonitoring.service.AnalysisService;
import com.major.unifiedmonitoring.service.CurrentUserService;
import jakarta.validation.Valid;
import org.springframework.core.io.Resource;
import org.springframework.core.io.UrlResource;
import org.springframework.http.MediaType;
import org.springframework.http.MediaTypeFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.net.MalformedURLException;
import java.nio.file.Path;
import java.util.List;

@RestController
@RequestMapping("/api/analysis")
public class AnalysisController {

    private final AnalysisService analysisService;
    private final CurrentUserService currentUserService;

    public AnalysisController(AnalysisService analysisService, CurrentUserService currentUserService) {
        this.analysisService = analysisService;
        this.currentUserService = currentUserService;
    }

    @PostMapping("/run")
    public ResponseEntity<AnalysisJobResponse> runAnalysis(@Valid @RequestBody RunAnalysisRequest request) {
        User user = currentUserService.getCurrentUserOrThrow();
        return ResponseEntity.ok(analysisService.submitJob(user.getId(), request));
    }

    @GetMapping("/jobs")
    public ResponseEntity<List<AnalysisJobResponse>> getJobs() {
        User user = currentUserService.getCurrentUserOrThrow();
        return ResponseEntity.ok(analysisService.getJobs(user.getId()));
    }

    @GetMapping("/jobs/{jobId}")
    public ResponseEntity<AnalysisJobResponse> getJob(@PathVariable Long jobId) {
        User user = currentUserService.getCurrentUserOrThrow();
        return ResponseEntity.ok(analysisService.getJob(user.getId(), jobId));
    }

    @GetMapping("/jobs/{jobId}/output")
    public ResponseEntity<Resource> getJobOutput(@PathVariable Long jobId) throws MalformedURLException {
        User user = currentUserService.getCurrentUserOrThrow();
        Path outputPath = analysisService.getJobOutputPathForUser(user.getId(), jobId);
        Resource resource = new UrlResource(outputPath.toUri());
        MediaType contentType = MediaTypeFactory.getMediaType(resource).orElse(MediaType.APPLICATION_OCTET_STREAM);
        return ResponseEntity.ok()
                .contentType(contentType)
                .body(resource);
    }
}
