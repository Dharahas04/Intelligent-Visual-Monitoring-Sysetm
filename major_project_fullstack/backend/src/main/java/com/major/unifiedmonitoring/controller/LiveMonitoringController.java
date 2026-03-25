package com.major.unifiedmonitoring.controller;

import com.major.unifiedmonitoring.service.LiveMonitoringService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/live")
public class LiveMonitoringController {

    private final LiveMonitoringService liveMonitoringService;

    public LiveMonitoringController(LiveMonitoringService liveMonitoringService) {
        this.liveMonitoringService = liveMonitoringService;
    }

    @GetMapping("/status")
    public Map<String, Object> getStatus() {
        return liveMonitoringService.statusSnapshot();
    }

    @GetMapping("/alerts")
    public List<Map<String, Object>> getRecentAlerts(@RequestParam(defaultValue = "30") int limit) {
        return liveMonitoringService.recentAlerts(limit);
    }
}
