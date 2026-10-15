# Compliance Status plugin

openmct plugin for the operator dashboard's **Compliance Status** panel — per-Framework,
per-Control status for an organization. First Phase-4 plugin (ADR-0015).

## Data flow

```
BFF  GET /compliance/status?org_id=   →  api.js (fetchComplianceStatus)
                                       →  transform.js (toViewModel)
                                       →  component.js (Vue 3 panel)
                                       →  plugin.js (openmct view provider)
```

The BFF owns the Standards×Evidence join (`app/app/l5/rollup.py`); this plugin only renders
the rolled-up payload. `transform.js` and `api.js` are framework-free and unit-tested headlessly.

## Usage (in the host)

```js
import ComplianceStatusPlugin from '@celestia/openmct-compliance-status';

openmct.install(ComplianceStatusPlugin({
  baseUrl: 'https://api.celestia.dynamics',
  orgId: '01ORG...',
  token: () => sessionToken()   // bearer forwarded to the BFF
}));
```

## Develop

```sh
bun install
bun test                # headless unit tests (transform + api)
bun run build           # bundle src/plugin.js (openmct external) → dist/
```

`openmct` is a **peer/external**: it is provided by the host at runtime (vendored at
`external/openmct/`, ADR-0003), never bundled here.

## Deferred (later Phase-4 slices)

- Drill-down from a control to its L1 evidence records (payload already carries `evidence`).
- Sub-control `evidence_required` coverage as a finer status tier (ADR-0015 §3).
- Browser/visual QA (`/design-review`, `/qa`) — this slice is build + unit-test only.
