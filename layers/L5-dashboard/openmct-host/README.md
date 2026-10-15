# openmct host

The Celestia operator dashboard host. Installs vendored openmct (ADR-0003) plus the Celestia
plugins and starts the app. First Phase-4 slice wires one plugin — Compliance Status (ADR-0015).

## Structure

- `src/index.js` — entry: installs openmct + Celestia plugins, reads runtime config from `window.CELESTIA`.
- `index.html` — loads vendored `openmct.js` + the host bundle; documents the runtime config contract.

## Develop

```sh
bun install
bun run build          # bundle src/index.js (openmct external) → dist/index.js
```

`openmct` is **external** in the build — provided at runtime from the vendored
`external/openmct/` (pinned SHA in `external/VENDOR.md`). Building the vendored openmct itself,
serving it behind nginx, and the shared-session-cookie auth handshake (ADR-0003 open question)
are part of the **deployment slice**, not this one. This slice's proof is a green `bun run build`
plus the plugin's headless unit tests.

## Config (`window.CELESTIA`)

| Key | Meaning |
| --- | --- |
| `baseUrl` | BFF base URL (default `/api`) |
| `orgId` | organization ULID to display |
| `token` | bearer token forwarded to the BFF |
| `openmctAssetPath` | path to openmct's built assets |
