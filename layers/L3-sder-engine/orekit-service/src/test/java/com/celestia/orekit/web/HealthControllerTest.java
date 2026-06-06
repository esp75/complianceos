package com.celestia.orekit.web;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.celestia.orekit.config.ReadinessState;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.web.servlet.MockMvc;

/**
 * Slices just the web layer; {@link ReadinessState} is mocked so we can exercise
 * both the ready and not-ready branches without loading orekit-data.
 */
@WebMvcTest(HealthController.class)
class HealthControllerTest {

    @Autowired
    private MockMvc mvc;

    @MockBean
    private ReadinessState readiness;

    @Test
    void healthzIsAlwaysOk() throws Exception {
        mvc.perform(get("/healthz"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("ok"));
    }

    @Test
    void readyzIs200WhenDataLoaded() throws Exception {
        when(readiness.isReady()).thenReturn(true);
        mvc.perform(get("/readyz"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("ready"));
    }

    @Test
    void readyzIs503WithErrorEnvelopeWhenNotReady() throws Exception {
        when(readiness.isReady()).thenReturn(false);
        when(readiness.detail()).thenReturn("orekit-data not loaded yet");
        mvc.perform(get("/readyz"))
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.error.code").value("not_ready"))
                .andExpect(jsonPath("$.error.message").value("orekit-data not loaded yet"));
    }
}
