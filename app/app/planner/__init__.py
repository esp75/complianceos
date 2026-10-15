"""Regulatory path planner (ADR-0018).

Turns a mission profile into a multi-jurisdiction licensing roadmap: which licences apply and
why (with citations to the law text), in what order, by when, and who to talk to. The knowledge
it plans from is open data under ``knowledge/`` at the repo root; the planning itself is
deterministic, so every date and citation in a roadmap can be traced and reproduced.
"""
