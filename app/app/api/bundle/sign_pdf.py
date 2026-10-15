# MARKED-FOR-EXTERNAL-REVIEW — Trail of Bits / Quarkslab / Cure53
"""Bundle PDF rendering + signature embedding (Phase 4, ADR-0016).

v0 ``BundleSigner``: render a human-readable compliance summary and embed a self-verifying sidecar
(the canonical manifest + detached Ed25519 signature + raw public key) as a PDF file attachment, so
any holder can re-verify offline with the org's public key alone. This is NOT yet full PAdES-B-LT
(CMS/X.509/timestamp) — that upgrade lands behind this same interface before the Quarkslab review.
PDF dates are pinned from ``issued_at`` so output is deterministic given the manifest.
"""

from __future__ import annotations

import datetime as _dt
import json
from typing import Any, Protocol, runtime_checkable

from fpdf import FPDF
from fpdf.enums import WrapMode

SIDECAR_BASENAME = "bundle-manifest.json"
_EPOCH = _dt.datetime(1970, 1, 1, tzinfo=_dt.UTC)


@runtime_checkable
class BundleSigner(Protocol):
    def render_and_sign(
        self, manifest: dict[str, Any], manifest_bytes: bytes, signature: bytes, pub_raw: bytes
    ) -> bytes: ...


def _fixed_date(issued_at: str) -> _dt.datetime:
    try:
        return _dt.datetime.fromisoformat(issued_at.replace("Z", "+00:00"))
    except ValueError:
        return _EPOCH


class DetachedEd25519PdfSigner:
    """v0 signer: summary page + embedded JSON sidecar carrying manifest, signature, public key."""

    def render_and_sign(
        self, manifest: dict[str, Any], manifest_bytes: bytes, signature: bytes, pub_raw: bytes
    ) -> bytes:
        issued_at = str(manifest.get("issued_at", ""))
        when = _fixed_date(issued_at)

        pdf = FPDF()
        pdf.set_creation_date(when)
        pdf.set_title(f"Compliance Evidence Bundle — {manifest.get('org_id', '')}")
        pdf.set_author("Celestia ComplianceOS")
        pdf.add_page()

        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Compliance Evidence Bundle", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, f"Organization: {manifest.get('org_id', '')}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, f"Issued: {issued_at}", new_x="LMARGIN", new_y="NEXT")

        summary = manifest.get("summary", {})
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Summary", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, (
            f"Compliant {summary.get('compliant', 0)} / Partial {summary.get('partial', 0)} / "
            f"Not assessed {summary.get('not_assessed', 0)}  "
            f"({summary.get('percentCompliant', 0)}% of {summary.get('total', 0)} controls)"
        ), new_x="LMARGIN", new_y="NEXT")

        for fw in manifest.get("frameworks", []):
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 7, f"{fw.get('shortName', '')} ({fw.get('framework', '')})",
                     new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            for ctrl in fw.get("controls", []):
                pdf.cell(0, 5, f"  {ctrl.get('refCode', '')}: {ctrl.get('status', '')} "
                               f"({ctrl.get('evidenceCount', 0)} evidence)",
                         new_x="LMARGIN", new_y="NEXT")

        merkle = manifest.get("merkle", {})
        key = manifest.get("key", {})
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Cryptographic seal", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Courier", "", 7)
        for label, value in (
            ("Merkle root (sha256):", merkle.get("root", "")),
            ("Key fingerprint:", key.get("fingerprint", "")),
            ("Signature (Ed25519):", signature.hex()),
        ):
            pdf.multi_cell(0, 4, f"{label} {value}", new_x="LMARGIN", new_y="NEXT",
                           wrapmode=WrapMode.CHAR)
        pdf.set_font("Helvetica", "", 8)
        pdf.ln(2)
        pdf.multi_cell(0, 4, "This bundle embeds a self-verifying sidecar "
                             f"('{SIDECAR_BASENAME}'): the canonical manifest, the detached Ed25519 "
                             "signature, and the issuing organization's public key. Verify offline "
                             "with the organization's published public key.",
                       new_x="LMARGIN", new_y="NEXT")

        sidecar = json.dumps(
            {
                "manifest": manifest,
                "signature_hex": signature.hex(),
                "public_key_hex": pub_raw.hex(),
                "alg": "Ed25519",
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        pdf.embed_file(
            bytes=sidecar,
            basename=SIDECAR_BASENAME,
            mime_type="application/json",
            creation_date=when,
            modification_date=when,
        )

        return bytes(pdf.output())
