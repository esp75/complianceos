package com.celestia.orekit.web;

import com.celestia.orekit.config.ReadinessState;
import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Liveness/readiness split mirroring the BFF's {@code app/app/api/health.py}.
 * {@code /healthz} never touches Orekit; {@code /readyz} is 200 only once
 * orekit-data is loaded, else 503 (CONTRACT.md).
 */
@RestController
public class HealthController {

    private final ReadinessState readiness;

    public HealthController(ReadinessState readiness) {
        this.readiness = readiness;
    }

    @GetMapping("/healthz")
    public Map<String, String> healthz() {
        return Map.of("status", "ok");
    }

    @GetMapping("/readyz")
    public ResponseEntity<?> readyz() {
        if (readiness.isReady()) {
            return ResponseEntity.ok(Map.of("status", "ready"));
        }
        return ResponseEntity.status(503).body(ErrorResponse.of("not_ready", readiness.detail()));
    }
}
