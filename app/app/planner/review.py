"""Reviewer package: the dossier as diff-friendly Markdown with a checklist (ADR-0022).

A licensing practitioner reviews the draft rules a roadmap rests on. This file is what they get:
every claim with its label and citation, every quoted provision with its source and retrieval date,
and a checklist per licence. The order is fixed and there are no timestamps beyond the roadmap date,
so two exports of the same data are identical and a change shows up as a plain diff."""

from __future__ import annotations

import re

from app.planner.brief import Brief
from app.planner.plan import Roadmap

_MARKER = re.compile(r"\[cite:([^\]]+)\]")


def _clean(text: str) -> str:
    return " ".join(_MARKER.sub(lambda m: f"[{m.group(1)}]", text).split())


def dossier_markdown(roadmap: Roadmap, brief: Brief) -> str:
    m = roadmap.mission
    lines = [
        f"# Licensing roadmap: {m.name}",
        "",
        f"Generated {roadmap.generated_on} · target launch {m.target_launch_date} · "
        f"{m.satellite_count} satellite(s), {m.orbit.value} · operator country {m.operator_country}",
        "",
        "> Information, not legal advice. Records marked draft are researched from official sources "
        "and not yet reviewed by a licensing practitioner.",
        "",
    ]

    claims = uncited = 0
    for section in brief.sections:
        if not section.paragraphs:
            continue
        lines += [f"## {section.title}", ""]
        for n, para in enumerate(section.paragraphs):
            label = section.labels[n] if n < len(section.labels) and section.labels[n] else ""
            if section.grounded:
                claims += 1
                uncited += 0 if _MARKER.search(para) else 1
            lines.append(f"- {f'`{label}` ' if label else ''}{_clean(para)}")
        lines.append("")

    if roadmap.warnings:
        lines += ["## Warnings", "", *(f"- {w}" for w in roadmap.warnings), ""]

    lines += ["## Licences and legal basis", ""]
    for item in sorted(roadmap.items, key=lambda i: i.license_id):
        auth = roadmap.authorities.get(item.authority_id)
        lines += [
            f"### {item.name} (`{item.license_id}`)",
            "",
            f"- Authority: {auth.authority.name if auth else item.authority_id}",
            f"- Status of the rule record: **{item.status.value}** (last verified {item.last_verified})",
            f"- Start by {item.start_by}; submit by {item.submit_by}; review "
            f"{item.review.min_weeks}-{item.review.max_weeks} weeks ({item.review.basis})",
            "",
        ]
        for reason in item.reasons:
            cites = f" [{', '.join(reason.cite)}]" if reason.cite else ""
            lines.append(f"- Why it applies: {reason.text}{cites}")
        lines.append("")
        for cid in item.legal_basis:
            c = roadmap.citations[cid]
            lines += [f"**{c.instrument}, {c.provision}** (`{c.id}`, {c.language})",
                      "",
                      f"> {(c.excerpt).strip()}"]
            if c.excerpt_en:
                lines += [">", f"> English (unofficial): {c.excerpt_en.strip()}"]
            lines += ["", f"Source: <{c.url}> · retrieved {c.retrieved}", ""]
        lines += [
            "Reviewer checklist:",
            "",
            *(f"- [ ] {q}" for q in (
                "Each quoted provision matches the source text at the URL above",
                "The reasons this licence applies to the mission are correct and complete",
                "No licence, filing or condition that applies is missing",
                "The processing time and its basis (statutory, practice or estimate) are right",
                "Fees and local-presence statements are right",
            )),
            "",
        ]

    lines += [
        "## Automated checks",
        "",
        f"- Grounded paragraphs: {claims}; without a citation: {uncited}",
        f"- Licences: {len(roadmap.items)}; rule records still draft: "
        f"{sum(1 for i in roadmap.items if i.status.value != 'reviewed')}",
        "",
        "## Reviewer sign-off",
        "",
        "- Reviewer (organisation):",
        "- Date:",
        "- Result: approved / approved with changes / not approved",
        "- Notes:",
        "",
    ]
    return "\n".join(lines)
