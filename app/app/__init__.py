"""Celestia ComplianceOS v0.2 — FastAPI orchestration / BFF layer.

This package is the Celestia-domain orchestration layer that sits in front of the
theopenlane/core L1 substrate (Go service, GraphQL on :17608). Per ADR-0001 and
ADR-0012, all access to theopenlane goes through GraphQL via ``app.clients.openlane``;
this layer never patches upstream Go.
"""
