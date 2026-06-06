package com.celestia.orekit.config;

import java.util.concurrent.atomic.AtomicBoolean;
import org.springframework.stereotype.Component;

/**
 * Holds whether orekit-data has been loaded, so the health controller can gate
 * {@code /readyz} on it without depending on the loader's internals. Set by
 * {@link OrekitDataConfig} at startup.
 */
@Component
public class ReadinessState {

    private final AtomicBoolean ready = new AtomicBoolean(false);
    private volatile String detail = "orekit-data not loaded yet";

    public boolean isReady() {
        return ready.get();
    }

    public String detail() {
        return detail;
    }

    void markReady() {
        this.detail = "orekit-data loaded";
        this.ready.set(true);
    }

    void markNotReady(String reason) {
        this.detail = reason;
        this.ready.set(false);
    }
}
