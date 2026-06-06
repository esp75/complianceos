package com.celestia.orekit.config;

import jakarta.annotation.PostConstruct;
import java.io.File;
import org.orekit.data.DataContext;
import org.orekit.data.DataProvidersManager;
import org.orekit.data.DirectoryCrawler;
import org.orekit.time.TimeScalesFactory;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * The linchpin of the service: Orekit cannot propagate without its data files
 * (EOP, leap seconds, gravity models). This registers a {@link DirectoryCrawler}
 * over a runtime-mounted data directory (ADR-0013 decision 5 — mounted volume,
 * not baked into the image) and verifies the load by resolving the UTC time
 * scale, which forces a leap-second read. {@code /readyz} gates on the result so
 * a missing-data misconfiguration surfaces at boot, not on the first request.
 */
@Component
public class OrekitDataConfig {

    private static final Logger log = LoggerFactory.getLogger(OrekitDataConfig.class);

    private final ReadinessState readiness;
    private final String dataPath;

    public OrekitDataConfig(
            ReadinessState readiness,
            @Value("${orekit.data.path:/orekit-data}") String dataPath) {
        this.readiness = readiness;
        this.dataPath = dataPath;
    }

    @PostConstruct
    void loadOrekitData() {
        File dataDir = new File(dataPath);
        if (!dataDir.isDirectory()) {
            String reason = "orekit-data directory not found at " + dataPath;
            log.error("{} — run scripts/fetch-orekit-data.sh and mount it read-only", reason);
            readiness.markNotReady(reason);
            return;
        }

        try {
            DataProvidersManager manager = DataContext.getDefault().getDataProvidersManager();
            manager.addProvider(new DirectoryCrawler(dataDir));
            // Force a real load: resolving UTC reads the leap-second files. If the
            // data set is empty or malformed this throws, and we stay not-ready.
            TimeScalesFactory.getUTC();
            log.info("orekit-data loaded from {}", dataPath);
            readiness.markReady();
        } catch (RuntimeException ex) {
            String reason = "failed to load orekit-data from " + dataPath + ": " + ex.getMessage();
            log.error(reason, ex);
            readiness.markNotReady(reason);
        }
    }
}
