package com.major.unifiedmonitoring.service;

import com.major.unifiedmonitoring.dto.ServiceResponse;
import com.major.unifiedmonitoring.model.AiService;
import org.springframework.stereotype.Service;

import java.util.Arrays;
import java.util.List;

@Service
public class ServiceCatalogService {

    public List<ServiceResponse> getAllServices() {
        return Arrays.stream(AiService.values())
                .map(service -> new ServiceResponse(
                        service.name(),
                        service.getTitle(),
                        service.getDescription()
                ))
                .toList();
    }
}
