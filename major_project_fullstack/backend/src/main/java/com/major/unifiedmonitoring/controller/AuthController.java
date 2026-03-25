package com.major.unifiedmonitoring.controller;

import com.major.unifiedmonitoring.dto.AuthRequest;
import com.major.unifiedmonitoring.dto.AuthResponse;
import com.major.unifiedmonitoring.dto.RegisterRequest;
import com.major.unifiedmonitoring.model.User;
import com.major.unifiedmonitoring.service.AuthService;
import com.major.unifiedmonitoring.service.CurrentUserService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthService authService;
    private final CurrentUserService currentUserService;

    public AuthController(AuthService authService, CurrentUserService currentUserService) {
        this.authService = authService;
        this.currentUserService = currentUserService;
    }

    @PostMapping("/register")
    public ResponseEntity<AuthResponse> register(@Valid @RequestBody RegisterRequest request) {
        return ResponseEntity.ok(authService.register(request));
    }

    @PostMapping("/login")
    public ResponseEntity<AuthResponse> login(@Valid @RequestBody AuthRequest request) {
        return ResponseEntity.ok(authService.login(request));
    }

    @GetMapping("/profile")
    public ResponseEntity<AuthResponse> profile() {
        User user = currentUserService.getCurrentUserOrThrow();
        return ResponseEntity.ok(new AuthResponse(null, user.getFullName(), user.getEmail()));
    }
}
