"""EUR-Lex / CELLAR access: fetch a CELEX document's HTML text and check citations.

Resolution path (verified against CELEX 52025PC0335 on 2026-10-27):
  1. GET publications.europa.eu/resource/celex/<CELEX> with Accept-Language
     returns HTTP 300 with a list of manifestations and their DOC_n stream URLs.
  2. The English act body is the stream named "*_EN_ACT_part1*.html".
  3. That stream is fetched directly as HTML and cached on disk.

Only the Python standard library and httpx are used for parsing.
"""

from __future__ import annotations

import hashlib
import html.parser
import re
from dataclasses import dataclass
from pathlib import Path

import httpx

CELEX_RE = re.compile(r"^[1-9][0-9]{4}[A-Z]{1,2}[0-9]{4}(\([0-9]{2}\))?$")
CELLAR_CELEX = "https://publications.europa.eu/resource/celex/{celex}"
DEFAULT_CACHE = Path(".cache/eurlex")
USER_AGENT = "complianceos-eurlex-mcp/0.1 (+https://github.com/esp75/complianceos)"


class CelexError(ValueError):
    """Bad CELEX id, or the document could not be resolved."""


@dataclass(frozen=True)
class Document:
    celex: str
    lang: str
    url: str
    text: str


@dataclass(frozen=True)
class Verification:
    verified: bool
    reason: str
    url: str | None


def validate_celex(celex: str) -> str:
    if not CELEX_RE.match(celex):
        raise CelexError(f"not a valid CELEX number: {celex!r}")
    return celex


class _TextExtractor(html.parser.HTMLParser):
    _SKIP = {"script", "style"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._SKIP:
            self._skip_depth += 1
        elif tag in {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)


def html_to_text(raw: str) -> str:
    extractor = _TextExtractor()
    extractor.feed(raw)
    text = "".join(extractor.parts)
    text = re.sub(r"[ \t\xa0]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


_STREAM_HTML = re.compile(r'title="stream_name">([^<]*_EN_ACT_part1[^<]*\.html)<', re.IGNORECASE)
_DOC_URL = re.compile(r'href="((?:https?)://publications\.europa\.eu/resource/cellar/[^"]+/DOC_\d+)"')
ALLOWED_HOST = "publications.europa.eu"


def pick_act_stream_url(listing: str) -> str:
    """From a CELLAR 300 listing, return the URL of the English act body stream.

    The listing pairs each DOC_n URL with a stream_name in the same <li> block,
    so walk the blocks in order and keep the URL that precedes the matching name.
    """
    blocks = listing.split('title="item"')
    for block in blocks:
        name = _STREAM_HTML.search(block)
        url = _DOC_URL.search(block)
        if name and url:
            return _secure_url(url.group(1))
    raise CelexError("no English act body stream in CELLAR listing")


def _secure_url(url: str) -> str:
    """Force https and require the CELLAR host. Listing URLs arrive as http://."""
    parsed = httpx.URL(url)
    if parsed.host != ALLOWED_HOST:
        raise CelexError(f"unexpected host in CELLAR listing: {parsed.host}")
    return str(parsed.copy_with(scheme="https"))


class EurLexClient:
    def __init__(
        self,
        *,
        cache_dir: Path = DEFAULT_CACHE,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._cache_dir = cache_dir
        self._client = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=timeout,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def _cache_path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode()).hexdigest()
        return self._cache_dir / f"{digest}.html"

    def fetch_celex(self, celex: str, lang: str = "EN") -> Document:
        celex = validate_celex(celex)
        if not re.fullmatch(r"[A-Z]{2}", lang):
            raise CelexError(f"bad language code {lang!r}")
        cache_file = self._cache_path(f"{celex}:{lang}")
        if cache_file.exists():
            raw = cache_file.read_text(encoding="utf-8")
            # Entries cached before the https fix still hold http:// URLs. Re-check on read.
            url = _secure_url(raw.split("\n", 1)[0])
            return Document(celex, lang, url, html_to_text(raw.split("\n", 1)[1]))

        # Accept: text/html makes CELLAR return the 300 manifestation list. Without it
        # the default RDF representation comes back and carries no stream URLs.
        listing = self._client.get(
            CELLAR_CELEX.format(celex=celex),
            headers={"Accept": "text/html", "Accept-Language": lang.lower()},
        )
        if listing.status_code not in (200, 300):
            raise CelexError(f"CELLAR returned {listing.status_code} for {celex}")
        url = pick_act_stream_url(listing.text)

        body = self._client.get(url)
        if body.status_code != 200:
            raise CelexError(f"CELLAR returned {body.status_code} for stream {url}")
        # Redirects are followed, so check where the body actually came from.
        final = body.url
        if final.scheme != "https" or final.host != ALLOWED_HOST:
            raise CelexError(f"stream redirected off CELLAR to {final}")

        self._cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(f"{url}\n{body.text}", encoding="utf-8")
        return Document(celex, lang, url, html_to_text(body.text))

    def verify_citation(
        self, celex: str, article: str, paragraph: str | None = None
    ) -> Verification:
        """Check that the article exists in the consolidated text of the given CELEX.

        Only article existence is checked. Paragraph and point are not verified
        and the reason says so. Semantic correctness is not checked here.
        """
        try:
            doc = self.fetch_celex(celex)
        except (CelexError, httpx.HTTPError) as exc:
            return Verification(False, f"could not fetch {celex}: {exc}", None)

        art = re.escape(article.strip())
        if not re.search(rf"(?m)^\s*Article\s+{art}\b", doc.text):
            return Verification(False, f"Article {article} not found in {celex}", doc.url)

        note = "article exists"
        if paragraph is not None:
            note += "; paragraph not checked"
        return Verification(True, note, doc.url)
