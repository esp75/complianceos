package com.celestia.orekit.service;

import com.celestia.orekit.error.ApiException;
import org.hipparchus.geometry.euclidean.threed.Vector3D;
import org.orekit.frames.Frame;
import org.orekit.frames.FramesFactory;
import org.orekit.propagation.analytical.tle.TLE;
import org.orekit.time.AbsoluteDate;
import org.orekit.time.TimeScalesFactory;
import org.orekit.utils.IERSConventions;

/** Shared boundary helpers: epoch parsing/formatting, TLE parsing, frame resolution,
 * and the meters↔km conversion that keeps the wire contract in km (CONTRACT.md). */
final class OrekitSupport {

    private static final double M_PER_KM = 1000.0;

    private OrekitSupport() {}

    /** Parse a UTC ISO-8601 epoch. A trailing 'Z' is accepted and stripped (Orekit's
     * parser takes the time scale explicitly rather than a zone suffix). */
    static AbsoluteDate parseEpoch(String epoch) {
        if (epoch == null || epoch.isBlank()) {
            throw new ApiException("invalid_request", "epoch is required");
        }
        String s = epoch.trim();
        if (s.endsWith("Z") || s.endsWith("z")) {
            s = s.substring(0, s.length() - 1);
        }
        try {
            return new AbsoluteDate(s, TimeScalesFactory.getUTC());
        } catch (RuntimeException ex) {
            throw new ApiException("invalid_request", "unparseable epoch '" + epoch + "': " + ex.getMessage());
        }
    }

    /** Format an AbsoluteDate as UTC ISO-8601 with a trailing 'Z'. */
    static String formatEpoch(AbsoluteDate date) {
        return date.toString(TimeScalesFactory.getUTC()) + "Z";
    }

    static TLE parseTle(com.celestia.orekit.domain.Dtos.TleDto tle) {
        if (tle == null || tle.line1() == null || tle.line2() == null) {
            throw new ApiException("invalid_tle", "tle.line1 and tle.line2 are required");
        }
        try {
            return new TLE(tle.line1(), tle.line2());
        } catch (RuntimeException ex) {
            throw new ApiException("invalid_tle", "malformed TLE: " + ex.getMessage());
        }
    }

    /** Resolve a frame name to an Orekit frame. Supports the CONTRACT.md set. */
    static Frame resolveFrame(String name) {
        if (name == null) {
            throw new ApiException("invalid_frame", "frame name is required");
        }
        return switch (name.trim().toUpperCase()) {
            case "EME2000", "J2000" -> FramesFactory.getEME2000();
            case "TEME" -> FramesFactory.getTEME();
            case "ITRF" -> FramesFactory.getITRF(IERSConventions.IERS_2010, true);
            default -> throw new ApiException("invalid_frame", "unknown frame '" + name + "'");
        };
    }

    static double[] toKm(Vector3D metres) {
        return new double[] {metres.getX() / M_PER_KM, metres.getY() / M_PER_KM, metres.getZ() / M_PER_KM};
    }

    static Vector3D fromKm(double[] km) {
        if (km == null || km.length != 3) {
            throw new ApiException("invalid_request", "expected a 3-element vector");
        }
        return new Vector3D(km[0] * M_PER_KM, km[1] * M_PER_KM, km[2] * M_PER_KM);
    }
}
