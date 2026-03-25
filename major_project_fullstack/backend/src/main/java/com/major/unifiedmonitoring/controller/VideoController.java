package com.major.unifiedmonitoring.controller;

import com.major.unifiedmonitoring.dto.VideoResponse;
import com.major.unifiedmonitoring.model.User;
import com.major.unifiedmonitoring.service.CurrentUserService;
import com.major.unifiedmonitoring.service.VideoService;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

@RestController
@RequestMapping("/api/videos")
public class VideoController {

    private final VideoService videoService;
    private final CurrentUserService currentUserService;

    public VideoController(VideoService videoService, CurrentUserService currentUserService) {
        this.videoService = videoService;
        this.currentUserService = currentUserService;
    }

    @PostMapping(value = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<VideoResponse> uploadVideo(@RequestPart("file") MultipartFile file) {
        User user = currentUserService.getCurrentUserOrThrow();
        return ResponseEntity.ok(videoService.uploadVideo(user.getId(), file));
    }

    @GetMapping
    public ResponseEntity<List<VideoResponse>> getVideos() {
        User user = currentUserService.getCurrentUserOrThrow();
        return ResponseEntity.ok(videoService.getVideosForUser(user.getId()));
    }
}
