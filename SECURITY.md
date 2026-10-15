# Security policy

## Reporting a vulnerability

Please report security issues privately through GitHub: **Security → Report a vulnerability** on
this repository. Do not open a public issue. We aim to acknowledge reports within 5 working days and
to agree a disclosure date with you.

Useful details: affected component (API, web app, knowledge validator, trust layer), steps to
reproduce, impact, and any suggested fix.

## Scope notes

- **Local mode** (the default) has no login by design, so the API checks that every request comes
  from this machine:
  - the peer, and any `X-Forwarded-For` hop, must be loopback or in
    `CELESTIA_LOCAL_ALLOWED_NETWORKS`;
  - `Host` and `X-Forwarded-Host` must be local names, which refuses other machines and
    DNS-rebinding pages;
  - changes need the `X-ComplianceOS-Client` header, which blocks cross-site request forgery.

  The web and API servers bind to 127.0.0.1 by default. Reaching a local instance from another
  machine, or making changes from another website, is a vulnerability. Binding the servers to all
  interfaces yourself is unsupported for local mode; use team mode to share.
- **Team mode** authorises every planner request with OpenFGA (`can_view` to read,
  `can_create_evidence` to change). Cross-workspace access is a vulnerability.
- **Knowledge pack**: contributed data is untrusted input. Contact values are validated by kind, and
  links are restricted to http(s), mailto and tel in the UI.
- **Trust layer** (`app/app/api/trust/**`, `app/app/api/bundle/sign*.py`) is reserved for a paid
  external review; known open findings are listed in [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md).
- Generated text (the optional Claude summary) must cite only sources already in the roadmap, or it
  is rejected. A way to get uncited or invented citations past that check is in scope.
