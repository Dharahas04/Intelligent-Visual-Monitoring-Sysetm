package com.major.unifiedmonitoring.service;

import com.major.unifiedmonitoring.dto.DashboardSummaryResponse;
import com.major.unifiedmonitoring.model.JobStatus;
import com.major.unifiedmonitoring.repository.AnalysisJobRepository;
import com.major.unifiedmonitoring.repository.VideoAssetRepository;
import org.springframework.stereotype.Service;

@Service
public class DashboardService {

    private final VideoAssetRepository videoAssetRepository;
    private final AnalysisJobRepository analysisJobRepository;

    public DashboardService(VideoAssetRepository videoAssetRepository, AnalysisJobRepository analysisJobRepository) {
        this.videoAssetRepository = videoAssetRepository;
        this.analysisJobRepository = analysisJobRepository;
    }

    public DashboardSummaryResponse getSummary(Long userId) {
        DashboardSummaryResponse response = new DashboardSummaryResponse();
        response.setTotalVideos(videoAssetRepository.countByUploadedById(userId));
        response.setTotalJobs(analysisJobRepository.countByRequestedById(userId));
        response.setRunningJobs(analysisJobRepository.countByRequestedByIdAndStatus(userId, JobStatus.RUNNING));
        response.setCompletedJobs(analysisJobRepository.countByRequestedByIdAndStatus(userId, JobStatus.COMPLETED));
        response.setFailedJobs(analysisJobRepository.countByRequestedByIdAndStatus(userId, JobStatus.FAILED));
        return response;
    }
}
