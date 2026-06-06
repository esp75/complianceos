package com.celestia.orekit.domain;

import java.util.List;

/**
 * Request/response DTOs for the three endpoints (CONTRACT.md). Positions are in km,
 * velocities in km/s, epochs UTC ISO-8601, frames one of EME2000 / ITRF / TEME.
 */
public final class Dtos {

    private Dtos() {}

    /** A two-line element set. */
    public record TleDto(String line1, String line2) {}

    /** A state vector at an epoch (km, km/s). */
    public record StateDto(double[] position, double[] velocity, String epoch) {}

    /** Standard state-vector response: position/velocity expressed in {@code frame}. */
    public record StateVectorResponse(double[] position, double[] velocity, String frame, String epoch) {}

    // --- /propagate ---
    public record PropagateRequest(TleDto tle, String epoch) {}

    // --- /conjunction ---
    public record WindowDto(String start, String end, double stepSeconds) {}

    public record ConjunctionRequest(TleDto tle1, TleDto tle2, WindowDto window, Double thresholdKm) {}

    public record ConjunctionEvent(String epoch, double missDistanceKm, double relativeSpeedKmS) {}

    public record ConjunctionResponse(List<ConjunctionEvent> events, double minMissDistanceKm) {}

    // --- /frame_convert ---
    public record FrameConvertRequest(StateDto state, String fromFrame, String toFrame) {}
}
