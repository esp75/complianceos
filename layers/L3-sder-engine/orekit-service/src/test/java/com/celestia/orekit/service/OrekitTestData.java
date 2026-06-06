package com.celestia.orekit.service;

import java.io.File;
import org.junit.jupiter.api.Assumptions;
import org.orekit.data.DataContext;
import org.orekit.data.DirectoryCrawler;
import org.orekit.time.TimeScalesFactory;

/**
 * Loads orekit-data into the test JVM from {@code -Dorekit.data.path} (or the
 * {@code OREKIT_DATA_PATH} env var, default {@code orekit-data}). When the data set is
 * absent the numeric tests are skipped via a JUnit assumption rather than failing, so the
 * suite is green without data; the verification run provides the data so they execute.
 */
final class OrekitTestData {

    private static boolean loaded = false;

    private OrekitTestData() {}

    static synchronized void ensureLoaded() {
        if (loaded) {
            return;
        }
        String path = System.getProperty(
                "orekit.data.path", System.getenv().getOrDefault("OREKIT_DATA_PATH", "orekit-data"));
        File dir = new File(path);
        Assumptions.assumeTrue(dir.isDirectory(), "orekit-data not available at " + path + " — skipping");
        DataContext.getDefault().getDataProvidersManager().addProvider(new DirectoryCrawler(dir));
        TimeScalesFactory.getUTC();  // force a real load; throws if the data set is unusable
        loaded = true;
    }
}
