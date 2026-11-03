# ComplianceOS v0.2 — Roadmap (refocused per ADR-0017, 2026-07-23)

> **Shipped 2026-10-15 (ADR-0018):** the open-source regulatory path planner covers much of P1 and
> P2 for five jurisdictions:
> - cited requirements map, sequencing and timeline, and signed deliverable;
> - client workspace with a program tracker, deadlines, contact log and calendar export.
>
> Still open from P1/P2: objection forecast, decision-maker map, the Watch's alert and history
> slices (first slice shipped 2026-11-01, ADR-0019), and corpus ingest beyond the hand-researched
> knowledge pack.

**First product:** AI regulatory-affairs for satellite operators — Market-Access Dossier → the Watch → program of record. The planner in this repository is the open-source core of that product.

**Foundation status:** the original Phase 0–4 first slices are **complete** and recorded in the [engineering log](docs/explanation/engineering-log.md) (L1 substrate + tetrad; L2 KG + ingest; L4 retrieval/drafting/citation-enforcer; trust-layer signed bundles; L3 Orekit and L5 openmct slices now **parked** per ADR-0017). ~60–70% of built code carries into the new product.

## Phase P1 — Dossier pipeline (weeks 1–2) · serves: pilot deliverable #1

**Goal:** produce a client-grade Market-Access Dossier for one pilot jurisdiction with the existing stack.

- [~] Jurisdiction corpus ingest v1 — Austria's space approval added by hand from the RIS API (DE not started: no verified sources; the L2 extractor was not used). Original text: point the L2 ingest (`app/app/kg/ingest.py` + Claude extractor) at national telecom/space acts, ministry publications, and ITU RR excerpts for the first 2–3 pilot jurisdictions (chosen by pilot signups; likely DE/AT/UK/LU from the target list)
- [~] Dossier composer — shipped ([ADR-0022](./adr/0022-dossier-sections-and-review-package.md)): friction points and decision-maker map, both citation-enforced, with basis labels; **open:** a sourced objection-pattern layer (practice data), L4 drafting of per-section prose. Original text: extend L4 drafting (`app/app/l4/drafting.py`) from single-obligation paragraphs to the dossier section set (requirements map, sequence/timeline, prerequisites, objection forecast, decision-maker map) — citation-or-422 enforced per section; practice-vs-statute confidence labels
- [~] Human-review loop — Markdown reviewer package with checklist shipped (ADR-0022); the branded-PDF part is unchanged: reviewer checklist + diff-friendly dossier format (markdown → branded PDF via existing fpdf2 path)
- [x] Signed deliverable — every dossier carries a verifiable Ed25519 signature over the roadmap and the brief ([ADR-0022](./adr/0022-dossier-sections-and-review-package.md) addendum), through the trust primitives (`/bundle/sign` seals Openlane evidence and is not the planner path). **Open:** pin the signer by fingerprint in a published verifier tool

**DoD:** one real-jurisdiction dossier passes expert review with zero uncited claims; produced end-to-end in ≤2 founder-days.

## Phase P2 — Workspace + the Watch v0 (weeks 3–6) · serves: pilot delivery + retention

- [x] Client workspace v0 (shipped with the planner, ADR-0018; Workspace page added): lightweight web UI (Next.js portal path per ADR-0003; replaces the parked openmct surface) — dossier viewer, program tracker (applications, deadlines, dependencies, statuses), tenant-isolated via L1 tetrad (roles: operator client, Celestia admin)
- [~] The Watch v0 — first slice shipped ([ADR-0019](./adr/0019-the-watch-v0.md)): every cited source checked on a schedule, change detection, changes linked to tracked applications, workspace feed and mission tab. alert email, PDF sources, curated publication feeds (GB, US) and advisory Claude triage shipped ([ADR-0020](./adr/0020-the-watch-alerts-pdf-feeds-triage.md)). **Open:** a Légifrance route (4 of 23 cited sources are blocked to automated fetches); more verified feeds (FR, LU, ITU, DE, AT); signed history (below). Per-workspace alert recipients shipped
- [~] Signed program history — first slice shipped ([ADR-0021](./adr/0021-signed-history-and-pilot-usage.md)): signed Merkle export of application events, chained across exports. **Open:** anchoring checkpoints in the trust layer's `trust_bundle` chain (needs a trust-layer change, after the external review)
- [~] Pilot instrumentation — first slice shipped (ADR-0021): session, mission, Watch and alert-link events with a summary endpoint. Dossier-export events and the pilot-facing report (Workspace page) shipped. **Open:** none beyond what pilots ask for

**DoD:** all pilot clients live in isolated workspaces; one real regulatory change detected → classified → alerted inside 48h.

## Phase P3 — Conversion hardening (weeks 7–12) · serves: pilots → paying clients

- [ ] Dossier pipeline cost/time reduction (target: ≤1 founder-day/dossier): section templates per jurisdiction archetype, reusable corpus, extraction QA harness
- [ ] Objection-pattern layer v1: structured objection/decision-maker records per jurisdiction accumulating in the KG (the compounding asset)
- [x] ~~Billing + subscription plumbing~~ dropped: the project is free and open source
- [~] Multi-jurisdiction workspace (the S2→S3 bridge: one client, N markets) — the Markets view (`GET /program`), per-application owners with a workload table, and a cross-mission source-changes list shipped; **open:** per-market (not per-application) ownership, if pilots ask
- [ ] `/cso` pass + RLS hardening on client-facing surfaces (licensing state is competitively sensitive — the sovereignty pitch must be true)

**DoD:** a converted client is billed, multi-market, monitored, with signed history — no founder heroics in the loop.

## Phase P4 — Scale prep (post-pilot, gated on conversions + pre-seed)

- Corpus expansion to 15–20 jurisdictions; delta-report lead-gen tool; advocacy-brief productization; EU IdP + full PAdES-B-LT (pre-audit, ADR-0016 seams); Quarkslab review (ADR-0011, unchanged); EU Space Act obligation stream as second product line (2028 horizon) — un-parks pieces of the original thesis.

## Parked (ADR-0017)

L3 Orekit service + ITU proximity + risk scoring (container shelved, code retained) · L5 openmct host + plugins · SDER/insurer surfaces · conjunction evidence flows. Revisit triggers in ADR-0017.

## Tooling cadence (unchanged)

Daily `/context-restore` / `/context-save` + `/retro`; per-PR `/review` (+`/cso` on auth/ingest/rag/trust/rls/bundle); `/careful` mandatory in trust paths; weekly `/health` + `/sync-gbrain`.

## Risk register (build-side)

| Risk | Mitigation |
|---|---|
| Dossier quality below client-grade on first jurisdictions | Expert review loop in P1 DoD; jurisdictions with checkable ground truth first; confidence labels |
| Watch monitoring brittle (ministry sites change/block) | Per-source adapters + failure alerts; start with official-journal/RSS-stable sources |
| Founder delivery time starves build time | P1/P2 scoped to serve delivery directly; anything not needed by a pilot is P3+ |
| Corpus ingest of non-EN sources (DE/FR/ES + later APAC) | Claude-extractor handles source language; dossier output EN; per-jurisdiction glossary in KG |
| Repo carries dormant space-specific code (L3/L5) | Parked, not deleted; excluded from active CI where slow |
