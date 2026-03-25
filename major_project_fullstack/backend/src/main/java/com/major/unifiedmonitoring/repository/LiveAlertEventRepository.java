package com.major.unifiedmonitoring.repository;

import com.major.unifiedmonitoring.model.LiveAlertEvent;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface LiveAlertEventRepository extends JpaRepository<LiveAlertEvent, Long> {
    List<LiveAlertEvent> findTop100ByOrderByCreatedAtDesc();
}
