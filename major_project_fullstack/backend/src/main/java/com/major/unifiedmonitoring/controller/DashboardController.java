package com.major.unifiedmonitoring.controller;

import com.major.unifiedmonitoring.dto.DashboardSummaryResponse;
import com.major.unifiedmonitoring.model.User;
import com.major.unifiedmonitoring.service.CurrentUserService;
import com.major.unifiedmonitoring.service.DashboardService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/dashboard")
public class DashboardController {

    private final DashboardService dashboardService;
    private final CurrentUserService currentUserService;

    public DashboardController(DashboardService dashboardService, CurrentUserService currentUserService) {
        this.dashboardService = dashboardService;
        this.currentUserService = currentUserService;
    }

    @GetMapping("/summary")
    public ResponseEntity<DashboardSummaryResponse> summary() {
        User user = currentUserService.getCurrentUserOrThrow();
        return ResponseEntity.ok(dashboardService.getSummary(user.getId()));
    }
}
