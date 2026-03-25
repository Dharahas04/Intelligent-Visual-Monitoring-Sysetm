package com.major.unifiedmonitoring.dto;

import com.major.unifiedmonitoring.model.AiService;
import jakarta.validation.constraints.NotNull;

public class RunAnalysisRequest {

    @NotNull
    private Long videoId;

    @NotNull
    private AiService serviceType;

    public Long getVideoId() {
        return videoId;
    }

    public void setVideoId(Long videoId) {
        this.videoId = videoId;
    }

    public AiService getServiceType() {
        return serviceType;
    }

    public void setServiceType(AiService serviceType) {
        this.serviceType = serviceType;
    }
}
