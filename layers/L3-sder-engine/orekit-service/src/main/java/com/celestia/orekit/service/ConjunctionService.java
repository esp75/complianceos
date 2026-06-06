package com.celestia.orekit.service;

import com.celestia.orekit.domain.Dtos.ConjunctionEvent;
import com.celestia.orekit.domain.Dtos.ConjunctionRequest;
import com.celestia.orekit.domain.Dtos.ConjunctionResponse;
import com.celestia.orekit.domain.Dtos.WindowDto;
import com.celestia.orekit.error.ApiException;
import java.util.ArrayList;
import java.util.List;
import org.orekit.frames.Frame;
import org.orekit.frames.FramesFactory;
import org.orekit.propagation.analytical.tle.TLE;
import org.orekit.propagation.analytical.tle.TLEPropagator;
import org.orekit.time.AbsoluteDate;
import org.orekit.utils.PVCoordinates;
import org.springframework.stereotype.Service;

/**
 * Conjunction screening, v0 = sampled minimum-miss-distance (ADR-0013). Both objects are
 * propagated in TEME across the window; the geometric range is sampled and local minima
 * below the reporting threshold are emitted as events. This is NOT probability-of-collision
 * (no covariance input) — see CONTRACT.md / METHODOLOGY.md.
 */
@Service
public class ConjunctionService {

    static final double DEFAULT_THRESHOLD_KM = 100.0;
    private static final double M_PER_KM = 1000.0;
    private static final int MAX_SAMPLES = 100_000;  // guard against pathological windows

    public ConjunctionResponse screen(ConjunctionRequest request) {
        WindowDto window = request.window();
        if (window == null) {
            throw new ApiException("invalid_window", "window is required");
        }
        double step = window.stepSeconds();
        if (step <= 0.0) {
            throw new ApiException("invalid_window", "stepSeconds must be positive");
        }
        AbsoluteDate start = OrekitSupport.parseEpoch(window.start());
        AbsoluteDate end = OrekitSupport.parseEpoch(window.end());
        double duration = end.durationFrom(start);
        if (duration <= 0.0) {
            throw new ApiException("invalid_window", "window end must be after start");
        }
        int steps = (int) Math.floor(duration / step);
        if (steps > MAX_SAMPLES) {
            throw new ApiException("invalid_window", "window/step yields too many samples (max " + MAX_SAMPLES + ")");
        }

        TLE tle1 = OrekitSupport.parseTle(request.tle1());
        TLE tle2 = OrekitSupport.parseTle(request.tle2());
        TLEPropagator p1 = TLEPropagator.selectExtrapolator(tle1);
        TLEPropagator p2 = TLEPropagator.selectExtrapolator(tle2);
        Frame teme = FramesFactory.getTEME();
        double thresholdKm = request.thresholdKm() != null ? request.thresholdKm() : DEFAULT_THRESHOLD_KM;

        List<AbsoluteDate> epochs = new ArrayList<>(steps + 1);
        List<Double> ranges = new ArrayList<>(steps + 1);
        List<Double> relSpeeds = new ArrayList<>(steps + 1);
        double minRange = Double.MAX_VALUE;

        for (int i = 0; i <= steps; i++) {
            AbsoluteDate t = start.shiftedBy(i * step);
            PVCoordinates pv1 = p1.getPVCoordinates(t, teme);
            PVCoordinates pv2 = p2.getPVCoordinates(t, teme);
            double rangeKm = pv1.getPosition().distance(pv2.getPosition()) / M_PER_KM;
            double relKmS = pv1.getVelocity().subtract(pv2.getVelocity()).getNorm() / M_PER_KM;
            epochs.add(t);
            ranges.add(rangeKm);
            relSpeeds.add(relKmS);
            minRange = Math.min(minRange, rangeKm);
        }

        List<ConjunctionEvent> events = new ArrayList<>();
        for (int i = 1; i < ranges.size() - 1; i++) {
            double r = ranges.get(i);
            // strict local minimum, at or below the reporting threshold
            if (r <= ranges.get(i - 1) && r < ranges.get(i + 1) && r <= thresholdKm) {
                events.add(new ConjunctionEvent(
                        OrekitSupport.formatEpoch(epochs.get(i)), round(r), round(relSpeeds.get(i))));
            }
        }

        return new ConjunctionResponse(events, round(minRange));
    }

    private static double round(double v) {
        return Math.round(v * 1000.0) / 1000.0;
    }
}
