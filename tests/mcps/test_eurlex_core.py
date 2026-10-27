from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from eurlex_core import (
    CelexError,
    EurLexClient,
    html_to_text,
    pick_act_stream_url,
    validate_celex,
)

LISTING = """<html><body><ul>
<li title="manifestation">cellar:x.0001.03<ul>
<li title="item"><a href="http://publications.europa.eu/resource/cellar/x.0001.03/DOC_1">
<span class="url">(http://publications.europa.eu/resource/cellar/x.0001.03/DOC_1)</span></a>
<ul><li title="stream_name">1_EN_ACT_part1_v7.html</li></ul></li>
<li title="item"><a href="http://publications.europa.eu/resource/cellar/x.0001.03/DOC_2">
<span class="url">(http://publications.europa.eu/resource/cellar/x.0001.03/DOC_2)</span></a>
<ul><li title="stream_name">1_EN_annexe_part1_v6.html</li></ul></li>
</ul></li></ul></body></html>"""

BODY = """<html><head><style>.x{}</style><script>var a=1;</script></head><body>
<p>Scope</p>
<p>Article 1</p><p>Subject matter.</p>
<p>Article 12</p><p>Conjunction monitoring.</p>
</body></html>"""


def test_pick_act_stream_selects_en_act_not_annex() -> None:
    assert pick_act_stream_url(LISTING).endswith("/DOC_1")


def test_pick_act_stream_forces_https() -> None:
    assert pick_act_stream_url(LISTING).startswith("https://publications.europa.eu/")


def test_pick_act_stream_rejects_foreign_host() -> None:
    evil = LISTING.replace("http://publications.europa.eu", "https://attacker.example")
    with pytest.raises(CelexError):
        pick_act_stream_url(evil)


def test_redirect_off_cellar_is_rejected(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/resource/celex/52025PC0335":
            return httpx.Response(300, text=LISTING)
        if request.url.host == "attacker.example":
            return httpx.Response(200, text=BODY)
        return httpx.Response(302, headers={"location": "https://attacker.example/x"})

    client = EurLexClient(cache_dir=tmp_path, transport=httpx.MockTransport(handler))
    with pytest.raises(CelexError):
        client.fetch_celex("52025PC0335")
    assert not any(tmp_path.iterdir())


def test_pick_act_stream_raises_when_missing() -> None:
    with pytest.raises(CelexError):
        pick_act_stream_url("<html>nothing</html>")


def test_html_to_text_drops_script_and_style() -> None:
    text = html_to_text(BODY)
    assert "var a" not in text
    assert ".x{}" not in text
    assert "Article 12" in text


def test_validate_celex_accepts_real_forms() -> None:
    assert validate_celex("52025PC0335") == "52025PC0335"
    assert validate_celex("32024R1689") == "32024R1689"


@pytest.mark.parametrize("bad", ["", "52025pc0335", "2025PC0335", "52025PC035", "x"])
def test_validate_celex_rejects_bad_forms(bad: str) -> None:
    with pytest.raises(CelexError):
        validate_celex(bad)


def _mock_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/resource/celex/52025PC0335":
            return httpx.Response(300, text=LISTING)
        if request.url.path == "/resource/cellar/x.0001.03/DOC_1":
            return httpx.Response(200, text=BODY)
        return httpx.Response(404, text="nope")

    return httpx.MockTransport(handler)


def _client(tmp_path: Path) -> EurLexClient:
    return EurLexClient(cache_dir=tmp_path, transport=_mock_transport())


def test_fetch_celex_resolves_and_caches(tmp_path: Path) -> None:
    client = _client(tmp_path)
    doc = client.fetch_celex("52025PC0335")
    assert doc.url.endswith("/DOC_1")
    assert "Conjunction monitoring." in doc.text
    assert any(tmp_path.iterdir())
    # Second call is served from cache: a transport that always fails must not be hit.
    broken = EurLexClient(
        cache_dir=tmp_path,
        transport=httpx.MockTransport(lambda r: httpx.Response(500)),
    )
    assert broken.fetch_celex("52025PC0335").text == doc.text


def test_verify_citation_finds_existing_article(tmp_path: Path) -> None:
    v = _client(tmp_path).verify_citation("52025PC0335", "12", paragraph="2")
    assert v.verified
    assert "paragraph not checked" in v.reason


def test_verify_citation_rejects_missing_article(tmp_path: Path) -> None:
    v = _client(tmp_path).verify_citation("52025PC0335", "99")
    assert not v.verified
    assert "not found" in v.reason


def test_verify_citation_does_not_match_prefix(tmp_path: Path) -> None:
    # Article 1 must not match Article 12 by prefix.
    client = _client(tmp_path)
    assert client.verify_citation("52025PC0335", "1").verified
    assert not client.verify_citation("52025PC0335", "1").reason.startswith("Article")


def test_verify_citation_reports_fetch_failure(tmp_path: Path) -> None:
    failing = EurLexClient(
        cache_dir=tmp_path, transport=httpx.MockTransport(lambda r: httpx.Response(503))
    )
    v = failing.verify_citation("52025PC0335", "12")
    assert not v.verified
    assert "could not fetch" in v.reason


def test_live_cellar_smoke() -> None:
    import os

    if not os.environ.get("EURLEX_LIVE"):
        pytest.skip("set EURLEX_LIVE=1 to hit publications.europa.eu")
    client = EurLexClient(cache_dir=Path(".cache/eurlex-live"))
    assert client.verify_citation("52025PC0335", "1").verified
    assert client.verify_citation("52025PC0335", "119").verified
    # 122 is past the last article (119) in the proposal. It must not verify.
    assert not client.verify_citation("52025PC0335", "122").verified
