#!/usr/bin/env bash
# Refresh gbrain pages from this repo's docs.
# Not yet a true CLI — invoke the gbrain MCP tools from within a Claude session.
# This script is the place to record the pages and links that should exist.
set -euo pipefail

cat <<'EOF'
gbrain ingestion is performed in-session by Claude Code via the gbrain MCP tools.

Pages that should exist:
  complianceos-overview
  layer-l1-substrate
  layer-l2-knowledge-graph
  layer-l3-sder-engine
  layer-l4-drafting-agent
  layer-l5-dashboards
  layer-cross-cutting
  adr-0001-theopenlane-core
  adr-0002-orekit-jvm-microservice
  adr-0003-openmct-and-nextjs
  adr-0004-lightrag-pattern
  adr-0005-trustgraph-context-cores
  adr-0006-compliancenlp-architecture
  adr-0007-postgres-age-pgvector
  adr-0008-accord-nlp-rase
  adr-0009-itu-compliance-port

Links to establish:
  complianceos-overview → every layer (link_type: contains)
  every layer → its governing ADRs (link_type: governed_by)
  ADRs → layers they affect (link_type: affects)

To regenerate, ask Claude Code:
  "Re-ingest the complianceOS v0.2 architecture into gbrain per scripts/ingest-to-gbrain.sh"
EOF
