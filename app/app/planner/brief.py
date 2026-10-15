"""Regulatory brief: the roadmap explained the way a senior regulatory-affairs lead would
(ADR-0018).

Sections: executive summary, critical path, risks, sequencing, questions to raise with each
authority, and where outside help exists. Everything is derived from the roadmap, so it is
reproducible offline. Sections that make legal claims are "grounded": every paragraph carries
``[cite:<id>]`` markers and is checked by the same enforcer as any generated text.

With an LLM configured (Claude via the Anthropic EU endpoint, ADR-0010), the model rewrites the
executive summary from the roadmap facts. Its text must cite only citations present in the
roadmap and cite in every paragraph, or the brief is rejected (:class:`CitationError`).
"""

from __future__ import annotations

import datetime as dt
import json
from typing import Literal

from pydantic import BaseModel

from app.l4.citations import CitationError, enforce_text_citations
from app.llm.base import LLMProvider
from app.planner.knowledge import Citation, Facilitator
from app.planner.plan import Roadmap, RoadmapItem

_SYSTEM = (
    "You are a senior regulatory-affairs executive for satellite operators. Write a short "
    "executive summary (two or three paragraphs) of the licensing roadmap you are given. Use only "
    "the facts provided. Every paragraph must cite its legal basis with inline markers written "
    "exactly as [cite:<id>], using only the citation ids listed. Do not invent requirements, "
    "dates, fees or citations. Plain, direct language; no filler."
)


class BriefSection(BaseModel):
    id: str
    title: str
    paragraphs: list[str]
    grounded: bool


class Brief(BaseModel):
    mission_name: str
    generated_on: dt.date
    mode: Literal["deterministic", "llm"]
    sections: list[BriefSection]
    citations: dict[str, Citation]
    facilitators: dict[str, Facilitator]


def _cite(ids: list[str]) -> str:
    return " ".join(f"[cite:{c}]" for c in ids)


def _date(d: dt.date) -> str:
    return d.strftime("%d %b %Y").lstrip("0")


def _authority_name(roadmap: Roadmap, item: RoadmapItem) -> str:
    found = roadmap.authorities.get(item.authority_id)
    return found.authority.name if found else item.authority_id


def _summary(r: Roadmap) -> list[str]:
    names = [j.name for j in r.jurisdictions]
    late = [i for i in r.items if i.risk == "late"]
    critical = [i for i in r.items if i.critical]
    first = r.items[0] if r.items else None
    paras = [
        f"To launch {r.mission.name} on {_date(r.mission.target_launch_date)}, the roadmap holds "
        f"{len(r.items)} licences, authorisations and filings across {', '.join(names)}. "
        + _cite([c for i in r.items for c in i.legal_basis[:1]])
    ]
    if critical:
        chain = " → ".join(i.name for i in critical)
        timing = (
            f"{len(late)} of them cannot be in place by their need date at typical processing "
            "times, so the dates need attention now."
            if late else "At typical processing times everything can be in place on time."
        )
        paras.append(f"The tightest chain is {chain}. {timing} "
                     + _cite([c for i in critical for c in i.legal_basis[:1]]))
    if first:
        paras.append(f"First action: start preparing the {first.name} by {_date(first.start_by)} "
                     f"with {_authority_name(r, first)}. " + _cite(first.legal_basis[:1]))
    return paras


def _critical(r: Roadmap) -> list[str]:
    out = []
    for i in (i for i in r.items if i.critical):
        why = i.reasons[0].text if i.reasons else ""
        out.append(
            f"{i.name} ({_authority_name(r, i)}): start by {_date(i.start_by)}, submit by "
            f"{_date(i.submit_by)}. Review typically takes {i.review.typical_weeks} weeks "
            f"({i.review.basis}). {why} " + _cite(i.legal_basis)
        )
    return out


def _risks(r: Roadmap) -> list[str]:
    out = []
    for i in r.items:
        if i.risk == "late":
            out.append(
                f"{i.name} cannot be granted by {_date(i.needed_by)} even if work starts today "
                f"(earliest grant {_date(i.earliest_grant)}). Move the date, or ask "
                f"{_authority_name(r, i)} about timing before committing to a launch slot. "
                + _cite(i.legal_basis[:1])
            )
        elif i.risk == "tight":
            out.append(f"{i.name} has less than four weeks of slack; any delay moves your launch. "
                       + _cite(i.legal_basis[:1]))
        if i.requires_local_presence:
            out.append(f"{i.name} requires a local presence: {i.local_presence_note} "
                       + _cite(i.legal_basis))
        if i.critical and i.review.basis == "estimate":
            out.append(f"There is no official processing time for {i.name}; the roadmap uses an "
                       f"estimate of {i.review.min_weeks}-{i.review.max_weeks} weeks. Confirm it "
                       "with the authority early. " + _cite(i.legal_basis[:1]))
        for o in i.obligations:
            if o.kind == "hard" and not o.recurring:
                out.append(f"{o.name} ({o.when}; {_date(o.due)} if you start now). {o.description} "
                           + _cite(o.cite or i.legal_basis[:1]))
    return out


def _sequence(r: Roadmap) -> list[str]:
    return [
        f"{n}. By {_date(i.start_by)}: start {i.name} ({_authority_name(r, i)}); submit by "
        f"{_date(i.submit_by)}. " + _cite(i.legal_basis[:1])
        for n, i in enumerate(r.items, start=1)
    ]


def _questions(r: Roadmap) -> list[str]:
    out = []
    international = {j.id for j in r.jurisdictions if j.kind == "international"}
    for aid, found in r.authorities.items():
        if found.jurisdiction in international:
            continue  # operators reach the ITU Bureau through their national administration
        mine = [i for i in r.items if i.authority_id == aid]
        qs = ["Is a pre-application meeting available, and who should we address?"]
        for i in mine:
            if i.review.basis == "estimate":
                qs.append(f"What is your current processing time for the {i.name}?")
            if i.requires_local_presence is None:
                qs.append(f"Do you require a local company or representative for the {i.name}?")
            if not i.fees:
                qs.append(f"Which fees apply to the {i.name}?")
        channels = "; ".join(f"{c.kind}: {c.value}" for c in found.authority.contacts)
        reach = f" Contact: {channels}." if channels else f" Website: {found.authority.website}."
        out.append(f"{found.authority.name}.{reach} Ask: " + " ".join(f"({k}) {q}" for k, q in
                                                                  enumerate(qs, start=1)))
    return out


def _support(r: Roadmap) -> list[str]:
    out = []
    for j in r.jurisdictions:
        firms = sorted({f for i in r.items if i.jurisdiction == j.id for f in i.facilitators})
        if firms:
            out.append(f"{j.name}: " + "; ".join(
                f"{r.facilitators[f].name} ({r.facilitators[f].website})" for f in firms) + ".")
        else:
            out.append(f"{j.name}: no firms listed yet. The directory is open to contributions.")
    return out


def _sections(r: Roadmap, summary: list[str]) -> list[BriefSection]:
    return [
        BriefSection(id="summary", title="Executive summary", paragraphs=summary, grounded=True),
        BriefSection(id="critical_path", title="Critical path", paragraphs=_critical(r), grounded=True),
        BriefSection(id="risks", title="Risks and hard deadlines", paragraphs=_risks(r), grounded=True),
        BriefSection(id="sequence", title="Recommended sequence", paragraphs=_sequence(r), grounded=True),
        BriefSection(id="questions", title="Questions to raise with each authority",
                     paragraphs=_questions(r), grounded=False),
        BriefSection(id="support", title="Outside help", paragraphs=_support(r), grounded=False),
    ]


def _check(sections: list[BriefSection], allowed: set[str]) -> None:
    for s in sections:
        if s.grounded and s.paragraphs:
            enforce_text_citations("\n\n".join(s.paragraphs), allowed)


def _facts(r: Roadmap) -> str:
    return json.dumps({
        "mission": r.mission.name,
        "launch": r.mission.target_launch_date.isoformat(),
        "licences": [
            {"name": i.name, "authority": _authority_name(r, i), "start_by": i.start_by.isoformat(),
             "submit_by": i.submit_by.isoformat(), "risk": i.risk, "critical": i.critical,
             "why": [x.text for x in i.reasons], "citation_ids": i.legal_basis}
            for i in r.items
        ],
        "warnings": r.warnings,
    }, indent=1)


async def build_brief(roadmap: Roadmap, llm: LLMProvider | None = None) -> Brief:
    allowed = set(roadmap.citations)
    summary = _summary(roadmap)
    mode: Literal["deterministic", "llm"] = "deterministic"
    if llm is not None and roadmap.items:
        text = await llm.complete(_SYSTEM, f"Roadmap facts:\n{_facts(roadmap)}\n\n"
                                           f"Allowed citation ids: {sorted(allowed)}")
        enforce_text_citations(text, allowed)  # raises CitationError: never return ungrounded text
        summary = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
        mode = "llm"
    sections = _sections(roadmap, summary)
    _check(sections, allowed)
    return Brief(
        mission_name=roadmap.mission.name,
        generated_on=roadmap.generated_on,
        mode=mode,
        sections=sections,
        citations=roadmap.citations,
        facilitators=roadmap.facilitators,
    )


__all__ = ["Brief", "BriefSection", "CitationError", "build_brief"]
