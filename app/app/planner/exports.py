"""Roadmap exports: calendar (ICS), dossier (signed PDF) and intro-email drafts (ADR-0018).

- ICS: every start, submission and obligation date as an all-day event, importable into any
  calendar, so deadlines live where people already look.
- Dossier: the roadmap, brief and quoted legal bases as a PDF with an embedded JSON sidecar. When a
  signing key is configured, the sidecar carries a detached Ed25519 signature over the canonical
  roadmap, made with the trust layer's KeyStore (ADR-0016); without one the PDF says it is
  unsigned rather than pretending otherwise.
- Intro email: a short, factual first message to an authority or facilitator, built from the
  roadmap (no model needed).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from typing import Any

from fpdf import FPDF
from fpdf.enums import WrapMode
from pydantic import BaseModel

from app.api.trust.keys import key_fingerprint, public_raw
from app.api.trust.keystore import KeyStore, KeyStoreUnavailable
from app.api.trust.signing import sign
from app.planner.brief import Brief
from app.planner.plan import Deadline, Roadmap, RoadmapItem

SIDECAR_NAME = "roadmap-signed.json"
_DISCLAIMER = ("Information, not legal advice. Records marked draft have been researched from "
               "official sources but not yet reviewed by a licensing practitioner. Confirm "
               "requirements with the competent authority before acting.")


# --- calendar ---

_LINE_BREAKS = re.compile(r"\r\n|[\r\n\x0b\x0c\x85\u2028\u2029]")
_CONTROL = re.compile(r"[\x00-\x08\x0e-\x1f\x7f]")


def _single_line(text: str) -> str:
    """User text with every kind of line break collapsed to a space and controls removed."""
    return _CONTROL.sub("", _LINE_BREAKS.sub(" ", text)).strip()


def _ics_escape(text: str) -> str:
    """RFC 5545 TEXT escaping. Every line-break form (including a bare CR and Unicode separators)
    becomes an escaped ``\\n`` and control characters are dropped, so user-supplied text (mission
    names, contact notes) can never start a new property line."""
    text = _CONTROL.sub("", text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,"))
    return _LINE_BREAKS.sub("\\\\n", text)


def _fold(line: str) -> list[str]:
    """RFC 5545 line folding at 75 octets."""
    data = line.encode("utf-8")
    out: list[str] = []
    while len(data) > 75:
        cut = 75 if not out else 74
        while cut > 0 and (data[cut] & 0xC0) == 0x80:  # never split a UTF-8 sequence
            cut -= 1
        out.append(data[:cut].decode("utf-8"))
        data = data[cut:]
    out.append(data.decode("utf-8"))
    return [out[0]] + [" " + part for part in out[1:]]


def calendar_ics(roadmap: Roadmap, mission_id: str, deadlines: list[Deadline] | None = None,
                 now: dt.datetime | None = None) -> str:
    stamp = (now or dt.datetime.now(dt.UTC)).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//ComplianceOS//Regulatory roadmap//EN",
             "CALSCALE:GREGORIAN", f"X-WR-CALNAME:{_ics_escape(roadmap.mission.name)} — licensing"]
    for n, d in enumerate(deadlines if deadlines is not None else roadmap.deadlines):
        day = d.date.strftime("%Y%m%d")
        nxt = (d.date + dt.timedelta(days=1)).strftime("%Y%m%d")
        prefix = "[HARD] " if d.hard else ""
        lines += [
            "BEGIN:VEVENT",
            f"UID:{mission_id}-{d.license_id}-{d.kind}-{n}@complianceos",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{day}",
            f"DTEND;VALUE=DATE:{nxt}",
            f"SUMMARY:{_ics_escape(prefix + d.title)}",
            f"DESCRIPTION:{_ics_escape(f'{roadmap.mission.name} · {d.license_id}. {_DISCLAIMER}')}",
            "TRANSP:TRANSPARENT",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(part for line in lines for part in _fold(line)) + "\r\n"


# --- dossier ---

_LATIN1 = str.maketrans({"—": "-", "–": "-", "→": "->", "’": "'", "‘": "'", "“": '"', "”": '"',
                         "œ": "oe", "Œ": "OE", "…": "...", "§": "§", "€": "EUR ", "\u00a0": " "})


def _t(text: str) -> str:
    """Core PDF fonts are Latin-1; map common typography and replace anything else."""
    return text.translate(_LATIN1).encode("latin-1", "replace").decode("latin-1")


class SignatureInfo(BaseModel):
    signed: bool
    algorithm: str | None = None
    fingerprint: str | None = None
    sha256: str
    note: str


def canonical_roadmap(roadmap: Roadmap) -> bytes:
    return json.dumps(roadmap.model_dump(mode="json"), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _sign(payload: bytes, keystore: KeyStore | None, workspace: str) -> tuple[SignatureInfo, dict[str, Any]]:
    digest = hashlib.sha256(payload).hexdigest()
    if keystore is not None:
        try:
            priv = keystore.signing_key(f"workspace:{workspace}")
        except KeyStoreUnavailable:
            priv = None
        if priv is not None:
            pub = public_raw(priv)
            sig = sign(payload, priv)
            info = SignatureInfo(signed=True, algorithm="Ed25519", fingerprint=key_fingerprint(pub),
                                 sha256=digest, note="Signed with this workspace's Ed25519 key.")
            return info, {"signature_hex": sig.hex(), "public_key_hex": pub.hex(), "alg": "Ed25519"}
    info = SignatureInfo(signed=False, sha256=digest,
                         note="Unsigned: no signing key is configured on this server.")
    return info, {}


class _Doc(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(110, 110, 110)
        self.cell(0, 5, _t(f"ComplianceOS · {_DISCLAIMER[:96]}…  Page {self.page_no()}"), align="C")


def _h(pdf: FPDF, text: str, size: int = 13) -> None:
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", size)
    pdf.set_text_color(15, 23, 42)
    pdf.multi_cell(0, size * 0.55, _t(text), new_x="LMARGIN", new_y="NEXT", align="L")
    pdf.set_text_color(30, 41, 59)
    pdf.ln(1)


def _p(pdf: FPDF, text: str, size: float = 9.5, style: str = "") -> None:
    pdf.set_font("Helvetica", style, size)
    pdf.multi_cell(0, size * 0.5, _t(text), new_x="LMARGIN", new_y="NEXT", align="L")
    pdf.ln(0.8)


def _strip_markers(text: str) -> str:
    return re.sub(r"\s*\[cite:([^\]]+)\]", r" [\1]", text).strip()


def _item_block(pdf: FPDF, r: Roadmap, i: RoadmapItem) -> None:
    auth = r.authorities.get(i.authority_id)
    _h(pdf, i.name, 11)
    _p(pdf, f"{auth.authority.name if auth else i.authority_id} · start by {i.start_by} · submit by "
            f"{i.submit_by} · review {i.review.min_weeks}-{i.review.max_weeks} weeks "
            f"({i.review.basis}) · {i.risk}{' · critical path' if i.critical else ''}", 8.5, "I")
    for reason in i.reasons:
        _p(pdf, f"- {reason.text}" + (f" [{', '.join(reason.cite)}]" if reason.cite else ""), 9)
    for cid in i.legal_basis:
        c = r.citations[cid]
        _p(pdf, f"{c.instrument}, {c.provision} [{c.id}]", 8.5, "B")
        _p(pdf, f"\"{(c.excerpt_en or c.excerpt).strip()}\"", 8.5)
        _p(pdf, f"{c.url} (retrieved {c.retrieved})", 7.5)
    for o in i.obligations:
        if o.occurrence == 1:
            _p(pdf, f"Obligation: {o.name} - {o.when} ({o.due} if started now).", 8.5)


def dossier_pdf(roadmap: Roadmap, brief: Brief, *, workspace: str,
                keystore: KeyStore | None) -> tuple[bytes, SignatureInfo]:
    payload = canonical_roadmap(roadmap)
    info, sig = _sign(payload, keystore, workspace)

    pdf = _Doc()
    when = dt.datetime.combine(roadmap.generated_on, dt.time(), tzinfo=dt.UTC)
    pdf.set_creation_date(when)
    pdf.set_title(_t(f"Licensing roadmap - {roadmap.mission.name}"))
    pdf.set_author("ComplianceOS")
    pdf.set_auto_page_break(True, margin=16)
    pdf.add_page()

    _h(pdf, f"Licensing roadmap: {roadmap.mission.name}", 17)
    m = roadmap.mission
    _p(pdf, f"Generated {roadmap.generated_on} · target launch {m.target_launch_date} · "
            f"{m.satellite_count} satellite(s), {m.orbit.value} · operator country {m.operator_country}",
       9, "I")
    _p(pdf, _DISCLAIMER, 8)

    for section in brief.sections:
        if not section.paragraphs:
            continue
        _h(pdf, section.title)
        for para in section.paragraphs:
            _p(pdf, _strip_markers(para))

    if roadmap.warnings:
        _h(pdf, "Warnings")
        for w in roadmap.warnings:
            _p(pdf, f"- {w}")

    _h(pdf, "Licences, authorisations and filings")
    for item in roadmap.items:
        _item_block(pdf, roadmap, item)

    _h(pdf, "Integrity")
    pdf.set_font("Courier", "", 7)
    pdf.multi_cell(0, 4, f"Roadmap SHA-256: {info.sha256}", new_x="LMARGIN", new_y="NEXT",
                   wrapmode=WrapMode.CHAR)
    if info.signed:
        pdf.multi_cell(0, 4, f"Ed25519 key fingerprint: {info.fingerprint}", new_x="LMARGIN",
                       new_y="NEXT", wrapmode=WrapMode.CHAR)
    _p(pdf, f"{info.note} The attached '{SIDECAR_NAME}' holds the exact roadmap"
            f"{', signature and public key' if info.signed else ''} so it can be checked offline.", 8)

    sidecar = json.dumps({"roadmap": json.loads(payload), "sha256": info.sha256, **sig},
                         sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    pdf.embed_file(bytes=sidecar, basename=SIDECAR_NAME, mime_type="application/json",
                   creation_date=when, modification_date=when)
    return bytes(pdf.output()), info


# --- intro email ---

class EmailDraft(BaseModel):
    to: str | None
    subject: str
    body: str


def intro_email(roadmap: Roadmap, item: RoadmapItem, recipient: str) -> EmailDraft:
    """A first message to an authority (by authority id) or a facilitator (by facilitator id)."""
    m = roadmap.mission
    operator = m.operator_name or "our company"
    facts = (f"{m.satellite_count} satellite(s) in {m.orbit.value}"
             + (f" at about {m.altitude_km:g} km" if m.altitude_km else "")
             + f", target launch {m.target_launch_date:%B %Y}")
    if recipient in roadmap.facilitators:
        f = roadmap.facilitators[recipient]
        subject = _single_line(f"Support with the {item.name}")
        body = (f"Hello {f.name} team,\n\n"
                f"{operator} is preparing {m.name} ({facts}). Our roadmap shows we need the "
                f"{item.name}, which we plan to submit by {item.submit_by:%d %B %Y}.\n\n"
                "Could you tell us whether you support this kind of application, how you usually "
                "work with operators at our stage, and what an engagement would involve?\n\n"
                "Kind regards,\n")
        return EmailDraft(to=str(f.website), subject=subject, body=body)
    found = roadmap.authorities.get(recipient)
    if found is None:
        raise KeyError(recipient)
    a = found.authority
    email = next((c.value for c in a.contacts if c.kind == "email"), None)
    questions = ["whether a pre-application meeting is available"]
    if item.review.basis == "estimate":
        questions.append("your current processing time")
    if item.requires_local_presence is None:
        questions.append("whether a local entity or representative is required")
    subject = _single_line(f"Pre-application enquiry: {item.name} for {m.name}")
    asks = questions[0] if len(questions) == 1 else ", ".join(questions[:-1]) + " and " + questions[-1]
    body = (f"Dear {a.name},\n\n"
            f"{operator} is preparing {m.name} ({facts}). We understand we will need the "
            f"{item.name} and would like to start early. We plan to submit by "
            f"{item.submit_by:%d %B %Y}.\n\n"
            f"Could you let us know {asks}?\n\n"
            "Kind regards,\n")
    return EmailDraft(to=email, subject=subject, body=body)
