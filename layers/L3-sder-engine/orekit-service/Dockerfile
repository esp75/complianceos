# Celestia L3 Orekit microservice. Multi-stage: build with the full JDK+Maven,
# run on a JRE-only base to keep the image lean (ADR-0013 — Spring Boot cold-start
# + image size is the top ops risk per ADR-0002).
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /build
# Dependencies first for layer caching.
COPY pom.xml .
RUN mvn -q -ntp dependency:go-offline
COPY src ./src
RUN mvn -q -ntp package -DskipTests

FROM eclipse-temurin:21-jre
# curl for the compose healthcheck (and ad-hoc debugging of /readyz).
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
COPY --from=build /build/target/orekit-service.jar app.jar
# orekit-data is mounted read-only at runtime, NOT baked in (ADR-0013 decision 5).
ENV OREKIT_DATA_PATH=/orekit-data
# Container-aware heap sizing.
ENV JAVA_OPTS="-XX:MaxRAMPercentage=75.0"
EXPOSE 8090
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]
