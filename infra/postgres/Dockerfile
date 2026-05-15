# Postgres 17 + Apache AGE + pgvector for the complianceOS reg-graph.
# The upstream apache/age image ships AGE but not pgvector — we layer it on.
FROM apache/age:release_PG17_1.6.0

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-17-pgvector \
    && rm -rf /var/lib/apt/lists/*
USER postgres
