"""Check that every URL cited in the knowledge pack still answers (weekly CI job).

Some official sites refuse automated clients (403) or are slow to answer; those are reported as
"blocked" or "timeout" rather than broken, because a person can still open them. Exit code 1 only
for URLs that are gone (404/410) or whose host no longer resolves or accepts connections.
"""

from __future__ import annotations

import sys

import httpx

from app.planner.knowledge import load_knowledge

UA = "ComplianceOS-link-check/1.0 (+https://github.com/; knowledge pack citation check)"


def urls() -> dict[str, list[str]]:
    kb = load_knowledge()
    found: dict[str, list[str]] = {}
    for lic in kb.licenses.values():
        for c in lic.legal_basis:
            found.setdefault(str(c.url), []).append(c.id)
        for s in lic.sources:
            found.setdefault(str(s.url), []).append(f"{lic.id} (source)")
    for j in kb.jurisdictions.values():
        for a in j.authorities:
            found.setdefault(str(a.website), []).append(a.id)
    for f in kb.facilitators.values():
        found.setdefault(str(f.website), []).append(f.id)
    return found


def main() -> int:
    broken = 0
    with httpx.Client(follow_redirects=True, timeout=30, headers={"User-Agent": UA}) as http:
        for url, refs in sorted(urls().items()):
            status = None
            for attempt in (1, 2):
                try:
                    status = http.get(url).status_code
                    break
                except httpx.TimeoutException:
                    if attempt == 2:
                        print(f"timeout {url} (check by hand)")
                except httpx.HTTPError as exc:
                    print(f"UNREACHABLE {url} ({exc.__class__.__name__}) used by {', '.join(refs)}")
                    broken += 1
                    break
            if status is None:
                continue
            if status in (404, 410):
                print(f"GONE {status} {url} used by {', '.join(refs)}")
                broken += 1
            elif status in (401, 403, 429):
                print(f"blocked {status} {url}")
            elif status >= 400:
                print(f"error {status} {url}")
    print(f"{broken} broken link(s)")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
