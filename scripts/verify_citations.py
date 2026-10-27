"""Verify every obligation citation in regulations/*.yaml. Exit 1 if any fails.

- kind=celex: the article must exist in the EUR-Lex text for that CELEX (live fetch,
  cached under .cache/eurlex). Paragraphs are not checked.
- other kinds: must carry a document_id or url (no network check yet).

This script does not write to the YAML files. It prints a JSON report.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "mcps" / "eurlex"))

from app.api.reggraph.loader import load_corpus  # noqa: E402
from eurlex_core import EurLexClient  # noqa: E402


def main() -> int:
    obligations = load_corpus(ROOT / "regulations")
    client = EurLexClient(cache_dir=ROOT / ".cache" / "eurlex")
    results: list[dict[str, object]] = []
    failed = 0
    try:
        for ob in obligations:
            c = ob.citation
            if c.kind == "celex":
                assert c.celex is not None
                v = client.verify_citation(c.celex, c.article, c.paragraph)
                ok, reason, url = v.verified, v.reason, v.url
            else:
                ok = bool(c.document_id or c.url)
                reason = "non-celex: identifier present" if ok else "missing document_id/url"
                url = c.url
            failed += 0 if ok else 1
            results.append({"id": ob.id, "ok": ok, "reason": reason, "source_url": url})
    finally:
        client.close()
    print(json.dumps({"checked": len(results), "failed": failed, "results": results}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
