package com.major.unifiedmonitoring.repository;

import com.major.unifiedmonitoring.model.AnalysisJob;
import com.major.unifiedmonitoring.model.JobStatus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface AnalysisJobRepository extends JpaRepository<AnalysisJob, Long> {
    List<AnalysisJob> findAllByRequestedByIdOrderByCreatedAtDesc(Long userId);
    java.util.Optional<AnalysisJob> findByIdAndRequestedById(Long id, Long userId);
    long countByRequestedById(Long userId);
    long countByRequestedByIdAndStatus(Long userId, JobStatus status);
}
