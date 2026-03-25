package com.major.unifiedmonitoring.repository;

import com.major.unifiedmonitoring.model.VideoAsset;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface VideoAssetRepository extends JpaRepository<VideoAsset, Long> {
    List<VideoAsset> findAllByUploadedByIdOrderByUploadedAtDesc(Long userId);
    long countByUploadedById(Long userId);
    Optional<VideoAsset> findByIdAndUploadedById(Long id, Long userId);
}
