package com.celestia.orekit.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.celestia.orekit.domain.Dtos.ConjunctionRequest;
import com.celestia.orekit.domain.Dtos.ConjunctionResponse;
import com.celestia.orekit.domain.Dtos.TleDto;
import com.celestia.orekit.domain.Dtos.WindowDto;
import com.celestia.orekit.error.ApiException;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

class ConjunctionServiceTest {

    private static final String L1 = "1 25544U 98067A   08264.51782528 -.00002182  00000-0 -11606-4 0  2927";
    private static final String L2 = "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537";

    private final ConjunctionService service = new ConjunctionService();

    @BeforeAll
    static void loadData() {
        OrekitTestData.ensureLoaded();
    }

    @Test
    void selfConjunctionHasZeroMissDistance() {
        WindowDto window = new WindowDto("2008-09-20T12:00:00Z", "2008-09-20T13:00:00Z", 60.0);
        ConjunctionResponse resp = service.screen(
                new ConjunctionRequest(new TleDto(L1, L2), new TleDto(L1, L2), window, null));
        // An object screened against itself is always co-located.
        assertEquals(0.0, resp.minMissDistanceKm(), 1e-3);
    }

    @Test
    void reportsAFiniteMinimumForTheWindow() {
        WindowDto window = new WindowDto("2008-09-20T12:00:00Z", "2008-09-20T12:30:00Z", 30.0);
        ConjunctionResponse resp = service.screen(
                new ConjunctionRequest(new TleDto(L1, L2), new TleDto(L1, L2), window, null));
        assertTrue(resp.minMissDistanceKm() >= 0.0);
    }

    @Test
    void invertedWindowRaisesInvalidWindow() {
        WindowDto window = new WindowDto("2008-09-20T13:00:00Z", "2008-09-20T12:00:00Z", 60.0);
        ApiException ex = assertThrows(
                ApiException.class,
                () -> service.screen(new ConjunctionRequest(new TleDto(L1, L2), new TleDto(L1, L2), window, null)));
        assertEquals("invalid_window", ex.code());
    }

    @Test
    void nonPositiveStepRaisesInvalidWindow() {
        WindowDto window = new WindowDto("2008-09-20T12:00:00Z", "2008-09-20T13:00:00Z", 0.0);
        ApiException ex = assertThrows(
                ApiException.class,
                () -> service.screen(new ConjunctionRequest(new TleDto(L1, L2), new TleDto(L1, L2), window, null)));
        assertEquals("invalid_window", ex.code());
    }
}
