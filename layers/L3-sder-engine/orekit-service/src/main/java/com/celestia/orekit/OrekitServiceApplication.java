package com.celestia.orekit;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/** Entry point for the Celestia L3 Orekit microservice (REST/JSON, ADR-0013). */
@SpringBootApplication
public class OrekitServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(OrekitServiceApplication.class, args);
    }
}
