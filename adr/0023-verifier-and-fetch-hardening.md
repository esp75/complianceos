# ADR-0023: Offline verifier and fetch hardening

Status: accepted (2026-11-01)

## Context

Signed dossiers and history exports embed their own public key, so a signature alone proves
integrity but not origin. The Watch fetches public URLs and sends SMTP mail, and a review found
two weak points: https redirects were followed without checking where they led, and SMTP could send
credentials in clear text.

## Decision

- **Verifier.** `verifier/complianceos_verify.py` is a single file (stdlib + `cryptography`) that
  checks a signed dossier or history export, and a history chain, with no ComplianceOS code or
  network. It exits 2 when the signer is not pinned by `--fingerprint`, so a script cannot mistake
  "unchanged" for "authentic". It re-implements the canonical form and Merkle rules; tests assert
  it agrees with the server's output.
- **Fetcher.** Redirects are followed by hand (max 5). Each hop must be https and resolve only to
  public addresses; a name that does not resolve is refused. After connecting, the peer address is
  checked again to narrow the DNS-rebinding window.
- **SMTP.** Unknown security values are rejected, and credentials are never sent with
  `security=none` unless the host is loopback.

## Consequences

The peer-address check runs after the request is sent and the response is discarded unread; it does
not stop the connection itself. Fully closing that needs connecting to a pre-validated IP with the
original host for SNI, left for a later change. Sources are pack URLs, not user input, which keeps
the exposure low.
