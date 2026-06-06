package com.celestia.orekit.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.celestia.orekit.domain.Dtos.PropagateRequest;
import com.celestia.orekit.domain.Dtos.StateDto;
import com.celestia.orekit.domain.Dtos.StateVectorResponse;
import com.celestia.orekit.domain.Dtos.TleDto;
import com.celestia.orekit.error.ApiException;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

class PropagationServiceTest {

    // Canonical ISS TLE (CelesTrak/Orekit example, epoch 2008-264).
    private static final String L1 = "1 25544U 98067A   08264.51782528 -.00002182  00000-0 -11606-4 0  2927";
    private static final String L2 = "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537";
    private static final String EPOCH = "2008-09-20T12:25:40Z";

    private final PropagationService service = new PropagationService();

    @BeforeAll
    static void loadData() {
        OrekitTestData.ensureLoaded();
    }

    private static double magnitude(double[] v) {
        return Math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
    }

    @Test
    void propagatesIssToAReasonableLeoPosition() {
        StateVectorResponse resp = service.propagate(new PropagateRequest(new TleDto(L1, L2), EPOCH));
        double radiusKm = magnitude(resp.position());
        // ISS orbital radius ~6780 km (R_earth 6378 + ~400 km altitude).
        assertTrue(radiusKm > 6600 && radiusKm < 7000, "unexpected ISS radius: " + radiusKm + " km");
        assertEquals("TEME", resp.frame());
    }

    @Test
    void malformedTleRaisesInvalidTle() {
        ApiException ex = assertThrows(
                ApiException.class,
                () -> service.propagate(new PropagateRequest(new TleDto("garbage", "garbage"), EPOCH)));
        assertEquals("invalid_tle", ex.code());
    }

    @Test
    void frameConversionPreservesPositionMagnitude() {
        // A pure frame rotation must preserve the position vector's norm.
        StateVectorResponse teme = service.propagate(new PropagateRequest(new TleDto(L1, L2), EPOCH));
        StateDto state = new StateDto(teme.position(), teme.velocity(), EPOCH);
        StateVectorResponse eme = service.convertFrame(state, "TEME", "EME2000");
        assertEquals(magnitude(teme.position()), magnitude(eme.position()), 1e-6);
        assertEquals("EME2000", eme.frame());
    }

    @Test
    void unknownFrameRaisesInvalidFrame() {
        StateDto state = new StateDto(new double[] {7000, 0, 0}, new double[] {0, 7.5, 0}, EPOCH);
        ApiException ex = assertThrows(
                ApiException.class, () -> service.convertFrame(state, "TEME", "BOGUS"));
        assertEquals("invalid_frame", ex.code());
    }
}
