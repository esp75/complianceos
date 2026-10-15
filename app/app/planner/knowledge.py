"""Knowledge pack: the open regulatory dataset the planner reasons over (ADR-0018).

Layout under ``knowledge/`` at the repo root::

    jurisdictions/<id>/jurisdiction.yaml      authorities + official contact channels
    jurisdictions/<id>/licenses/<id>.yaml     one licence / authorisation / filing type each
    facilitators/<id>.yaml                    third-party licensing firms (neutral listing)

Models are strict (unknown keys are errors) because this data is contributed by people through
pull requests and a typo must fail validation rather than silently drop a rule. Validation runs
in two passes: per-file schema checks, then cross-references across the whole pack (authorities,
prerequisites, citation ids, cycles). All problems are collected and reported together.

CLI::

    python -m app.planner.knowledge validate [--dir PATH]
    python -m app.planner.knowledge schema   [--out DIR]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from collections.abc import Iterator
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    ValidationError,
    model_validator,
)

from app.planner.mission import FACT_FIELDS

KNOWLEDGE_DIR = Path(
    os.environ.get(
        "CELESTIA_KNOWLEDGE_DIR",
        str(Path(__file__).resolve().parents[3] / "knowledge"),
    )
)

Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(?:[-.][a-z0-9]+)*$", max_length=120)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class ReviewStatus(StrEnum):
    #: Researched from official sources, not yet checked by a licensing practitioner.
    DRAFT = "draft"
    #: Checked by a practitioner; ``reviewed_by`` says who (organisation, not a person).
    REVIEWED = "reviewed"


class Source(_Strict):
    title: str
    url: HttpUrl
    retrieved: dt.date


class Citation(_Strict):
    """A pinpoint reference to the text of a legal instrument.

    ``excerpt`` is quoted verbatim in the instrument's language; ``excerpt_en`` is an unofficial
    English rendering when the original is not English.
    """

    id: Slug
    instrument: str
    provision: str
    url: HttpUrl
    retrieved: dt.date
    language: Annotated[str, StringConstraints(pattern=r"^[a-z]{2}$")]
    excerpt: Annotated[str, StringConstraints(min_length=1, max_length=1200)]
    excerpt_en: Annotated[str, StringConstraints(max_length=1200)] | None = None

    @model_validator(mode="after")
    def _translation_when_not_english(self) -> Citation:
        if self.language != "en" and not self.excerpt_en:
            raise ValueError(f"citation {self.id!r} is in {self.language!r}; add excerpt_en")
        return self


class AuthorityRole(StrEnum):
    SPACE_ACTIVITY_LICENSING = "space_activity_licensing"
    TECHNICAL_ASSESSMENT = "technical_assessment"
    SPECTRUM_MANAGEMENT = "spectrum_management"
    ITU_NOTIFYING_ADMINISTRATION = "itu_notifying_administration"
    MARKET_ACCESS = "market_access"
    EARTH_STATION_LICENSING = "earth_station_licensing"
    REMOTE_SENSING_LICENSING = "remote_sensing_licensing"
    LAUNCH_LICENSING = "launch_licensing"
    REGISTRATION = "registration"
    INTERNATIONAL_COORDINATION = "international_coordination"


class ContactChannel(_Strict):
    """An institutional contact channel as published by the authority itself.

    Named individuals are only recorded where the authority publishes them in an official
    capacity (CONTRIBUTING.md, "Contacts policy").
    """

    kind: Literal["web", "web_form", "portal", "email", "phone", "postal"]
    value: str
    purpose: str
    source: Source


class Authority(_Strict):
    id: Slug
    name: str
    name_en: str | None = None
    roles: list[AuthorityRole] = Field(min_length=1)
    website: HttpUrl
    contacts: list[ContactChannel] = Field(default_factory=list)
    notes: str | None = None


class Jurisdiction(_Strict):
    id: Slug
    name: str
    kind: Literal["national", "international"]
    #: ISO 3166-1 alpha-2 for national jurisdictions (``GB`` for the UK).
    country: Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")] | None = None
    summary: str
    authorities: list[Authority] = Field(min_length=1)
    status: ReviewStatus
    last_verified: dt.date
    reviewed_by: str | None = None

    @model_validator(mode="after")
    def _country_matches_kind(self) -> Jurisdiction:
        if self.kind == "national" and not self.country:
            raise ValueError(f"national jurisdiction {self.id!r} needs a country code")
        return self


class Rule(_Strict):
    """Applicability rule. Exactly one of: ``all``, ``any``, ``not``, or a ``field`` test.

    A field test uses exactly one operator: ``eq``, ``in``, ``contains`` (list fact contains the
    value), ``intersects`` (list fact shares a value with the list), ``gte`` / ``lte`` (numbers),
    or ``present`` (fact is set / non-empty). ``because`` and ``cite`` explain a match to the user.
    """

    all: list[Rule] | None = None
    any: list[Rule] | None = None
    not_: Rule | None = Field(default=None, alias="not")
    always: Literal[True] | None = None
    field: str | None = None
    eq: str | int | float | bool | None = None
    in_: list[str] | None = Field(default=None, alias="in")
    contains: str | None = None
    intersects: list[str] | None = None
    gte: float | None = None
    lte: float | None = None
    present: bool | None = None
    because: str | None = None
    cite: list[Slug] = Field(default_factory=list)

    @model_validator(mode="after")
    def _shape(self) -> Rule:
        kinds = [k for k in ("all", "any", "not_", "always", "field") if getattr(self, k) is not None]
        if len(kinds) != 1:
            raise ValueError(f"a rule needs exactly one of all/any/not/always/field, got {kinds or 'none'}")
        ops = [o for o in ("eq", "in_", "contains", "intersects", "gte", "lte", "present")
               if getattr(self, o) is not None]
        if self.field is None:
            if ops:
                raise ValueError(f"operators {ops} need a field")
            return self
        if self.field not in FACT_FIELDS:
            raise ValueError(f"unknown field {self.field!r}; known: {sorted(FACT_FIELDS)}")
        if len(ops) != 1:
            raise ValueError(f"field {self.field!r} needs exactly one operator, got {ops or 'none'}")
        is_list = FACT_FIELDS[self.field]
        if ops[0] in ("contains", "intersects") and not is_list:
            raise ValueError(f"{ops[0]} only applies to list fields; {self.field!r} is scalar")
        if ops[0] in ("eq", "in_", "gte", "lte") and is_list:
            raise ValueError(f"{ops[0].rstrip('_')} only applies to scalar fields; {self.field!r} is a list")
        return self

    def walk(self) -> Iterator[Rule]:
        yield self
        for child in (self.all or []) + (self.any or []) + ([self.not_] if self.not_ else []):
            yield from child.walk()


class Duration(_Strict):
    """Elapsed time in weeks, with where the numbers come from.

    ``statutory``: a deadline fixed in law; ``practice``: the authority's published guidance or
    service standard; ``estimate``: no official figure, judgement from experience.
    """

    min_weeks: int = Field(ge=0)
    typical_weeks: int = Field(ge=0)
    max_weeks: int = Field(ge=0)
    basis: Literal["statutory", "practice", "estimate"]
    note: str | None = None
    cite: list[Slug] = Field(default_factory=list)
    source: Source | None = None

    @model_validator(mode="after")
    def _ordered(self) -> Duration:
        if not self.min_weeks <= self.typical_weeks <= self.max_weeks:
            raise ValueError("need min_weeks <= typical_weeks <= max_weeks")
        if self.basis != "estimate" and not (self.cite or self.source):
            raise ValueError(f"a {self.basis} duration needs a cite or a source")
        return self


class Offset(_Strict):
    years: int = 0
    months: int = 0
    weeks: int = 0
    days: int = 0


class Obligation(_Strict):
    """A dated duty that follows from a licence: a deadline, a renewal, a recurring report.

    ``applies_when`` narrows it to some missions (e.g. constellation milestones); omitted means it
    always comes with the licence.
    """

    id: Slug
    name: str
    description: str
    anchor: Literal["submitted", "granted", "launch", "service_start"]
    offset: Offset = Offset()
    repeat_every: Offset | None = None
    kind: Literal["hard", "soft"]
    applies_when: Rule | None = None
    cite: list[Slug] = Field(default_factory=list)


class SubmissionWindow(_Strict):
    """The earliest a submission may be made, counted back from the date the licence is needed
    (e.g. an ITU notice may not reach the Bureau more than three years before bringing into use)."""

    opens_before_need: Offset
    note: str
    cite: list[Slug] = Field(default_factory=list)


class Prerequisite(_Strict):
    """Ordering constraint: this licence's submission waits for ``license`` to reach ``stage``.

    Only applies when both licences are in the plan; a prerequisite that does not apply to the
    mission is dropped, so one licence can list alternatives (e.g. each country's ITU route).
    """

    license: Slug
    stage: Literal["submitted", "granted"] = "granted"
    note: str | None = None


class LicenseCategory(StrEnum):
    SPACE_ACTIVITY = "space_activity"
    ITU_FILING = "itu_filing"
    SPECTRUM = "spectrum"
    EARTH_STATION = "earth_station"
    MARKET_ACCESS = "market_access"
    REMOTE_SENSING = "remote_sensing"
    LAUNCH = "launch"
    REGISTRATION = "registration"


class License(_Strict):
    id: Slug
    jurisdiction: Slug
    name: str
    name_local: str | None = None
    authority: Slug
    category: LicenseCategory
    summary: str
    applies_when: Rule
    legal_basis: list[Citation] = Field(min_length=1)
    prerequisites: list[Prerequisite] = Field(default_factory=list)
    needed_by: Literal["launch", "service_start"] = "launch"
    submission_window: SubmissionWindow | None = None
    preparation: Duration
    review: Duration
    documents: list[str] = Field(default_factory=list)
    fees: str | None = None
    obligations: list[Obligation] = Field(default_factory=list)
    #: True when a local company, representative or agent is required. ``None`` = not established.
    requires_local_presence: bool | None = None
    local_presence_note: str | None = None
    status: ReviewStatus
    last_verified: dt.date
    reviewed_by: str | None = None
    sources: list[Source] = Field(default_factory=list)


class Facilitator(_Strict):
    """A third-party firm that helps operators through licensing. Listing is neutral: no ranking,
    no paid placement, firm-level public information only (CONTRIBUTING.md, "Facilitators")."""

    id: Slug
    name: str
    kind: Literal["consultancy", "law_firm", "engineering", "industry_body"]
    jurisdictions: list[Slug] = Field(min_length=1)
    services: list[LicenseCategory] = Field(min_length=1)
    hq_country: Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]
    website: HttpUrl
    description: Annotated[str, StringConstraints(max_length=400)]
    source: Source
    listed_since: dt.date


class KnowledgeBase(BaseModel):
    model_config = ConfigDict(frozen=True)

    jurisdictions: dict[str, Jurisdiction]
    licenses: dict[str, License]
    facilitators: dict[str, Facilitator]

    @property
    def citations(self) -> dict[str, Citation]:
        return {c.id: c for lic in self.licenses.values() for c in lic.legal_basis}

    def authority(self, authority_id: str) -> tuple[Jurisdiction, Authority] | None:
        for j in self.jurisdictions.values():
            for a in j.authorities:
                if a.id == authority_id:
                    return j, a
        return None

    def facilitators_for(self, jurisdiction: str, category: LicenseCategory | None = None) -> list[Facilitator]:
        return [
            f for f in self.facilitators.values()
            if jurisdiction in f.jurisdictions and (category is None or category in f.services)
        ]


class KnowledgeError(ValueError):
    """Raised with every problem found, one per line, so a contributor can fix them all at once."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("\n".join(problems))


def _read_yaml(path: Path, problems: list[str]) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        problems.append(f"{path}: invalid YAML: {exc}")
        return None


def _parse[M: BaseModel](model: type[M], path: Path, problems: list[str]) -> M | None:
    data = _read_yaml(path, problems)
    if data is None:
        return None
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        for err in exc.errors():
            loc = ".".join(str(p) for p in err["loc"]) or "(root)"
            problems.append(f"{path}: {loc}: {err['msg']}")
        return None


def _find_cycle(edges: dict[str, list[str]]) -> list[str] | None:
    """Return one cycle in the prerequisite graph as a path, or None."""
    state: dict[str, int] = {}  # 1 = on stack, 2 = done
    stack: list[str] = []

    def visit(node: str) -> list[str] | None:
        state[node] = 1
        stack.append(node)
        for nxt in edges.get(node, []):
            if state.get(nxt) == 1:
                return stack[stack.index(nxt):] + [nxt]
            if nxt not in state and (found := visit(nxt)):
                return found
        stack.pop()
        state[node] = 2
        return None

    for node in sorted(edges):
        if node not in state and (found := visit(node)):
            return found
    return None


def _cross_check(kb_j: dict[str, Jurisdiction], kb_l: dict[str, License],
                 kb_f: dict[str, Facilitator], problems: list[str]) -> None:
    authorities = {a.id: j.id for j in kb_j.values() for a in j.authorities}
    if len(authorities) != sum(len(j.authorities) for j in kb_j.values()):
        problems.append("authority ids must be unique across all jurisdictions")

    citations: dict[str, str] = {}
    for lic in kb_l.values():
        for c in lic.legal_basis:
            if c.id in citations:
                problems.append(f"citation id {c.id!r} defined in both {citations[c.id]} and {lic.id}")
            citations[c.id] = lic.id

    for lic in kb_l.values():
        where = f"license {lic.id}"
        if lic.jurisdiction not in kb_j:
            problems.append(f"{where}: unknown jurisdiction {lic.jurisdiction!r}")
        if lic.authority not in authorities:
            problems.append(f"{where}: unknown authority {lic.authority!r}")
        for p in lic.prerequisites:
            if p.license not in kb_l:
                problems.append(f"{where}: prerequisite {p.license!r} does not exist")
            if p.license == lic.id:
                problems.append(f"{where}: lists itself as a prerequisite")
        cited = [c for r in lic.applies_when.walk() for c in r.cite]
        cited += lic.preparation.cite + lic.review.cite
        cited += lic.submission_window.cite if lic.submission_window else []
        for o in lic.obligations:
            cited += o.cite
            cited += [c for r in o.applies_when.walk() for c in r.cite] if o.applies_when else []
        for cid in cited:
            if cid not in citations:
                problems.append(f"{where}: cites unknown citation {cid!r}")

    cycle = _find_cycle({lic.id: [p.license for p in lic.prerequisites] for lic in kb_l.values()})
    if cycle:
        problems.append("prerequisite cycle: " + " -> ".join(cycle))

    for f in kb_f.values():
        for jid in f.jurisdictions:
            if jid not in kb_j:
                problems.append(f"facilitator {f.id}: unknown jurisdiction {jid!r}")


def load_knowledge(base: Path | None = None) -> KnowledgeBase:
    """Load and validate the whole pack. Raises :class:`KnowledgeError` listing every problem."""
    root = base or KNOWLEDGE_DIR
    problems: list[str] = []
    jurisdictions: dict[str, Jurisdiction] = {}
    licenses: dict[str, License] = {}
    facilitators: dict[str, Facilitator] = {}

    jdir = root / "jurisdictions"
    if not jdir.is_dir():
        raise KnowledgeError([f"{jdir}: no jurisdictions directory"])

    for d in sorted(p for p in jdir.iterdir() if p.is_dir()):
        jpath = d / "jurisdiction.yaml"
        if not jpath.exists():
            problems.append(f"{d}: missing jurisdiction.yaml")
            continue
        j = _parse(Jurisdiction, jpath, problems)
        if j is None:
            continue
        if j.id != d.name:
            problems.append(f"{jpath}: id {j.id!r} must match its directory name {d.name!r}")
        jurisdictions[j.id] = j
        for lpath in sorted((d / "licenses").glob("*.yaml")):
            lic = _parse(License, lpath, problems)
            if lic is None:
                continue
            if lic.id != lpath.stem:
                problems.append(f"{lpath}: id {lic.id!r} must match its file name")
            if lic.jurisdiction != j.id:
                problems.append(f"{lpath}: jurisdiction {lic.jurisdiction!r} must be {j.id!r}")
            if lic.id in licenses:
                problems.append(f"{lpath}: duplicate license id {lic.id!r}")
            licenses[lic.id] = lic

    for fpath in sorted((root / "facilitators").glob("*.yaml")):
        fac = _parse(Facilitator, fpath, problems)
        if fac is None:
            continue
        if fac.id != fpath.stem:
            problems.append(f"{fpath}: id {fac.id!r} must match its file name")
        facilitators[fac.id] = fac

    _cross_check(jurisdictions, licenses, facilitators, problems)
    if problems:
        raise KnowledgeError(problems)
    return KnowledgeBase(jurisdictions=jurisdictions, licenses=licenses, facilitators=facilitators)


def export_json_schema(out: Path) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name, model in (("jurisdiction", Jurisdiction), ("license", License), ("facilitator", Facilitator)):
        path = out / f"{name}.schema.json"
        path.write_text(json.dumps(model.model_json_schema(by_alias=True), indent=2) + "\n", encoding="utf-8")
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.planner.knowledge")
    sub = parser.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate", help="validate the knowledge pack")
    v.add_argument("--dir", type=Path, default=None)
    s = sub.add_parser("schema", help="export JSON Schema for editors")
    s.add_argument("--out", type=Path, default=KNOWLEDGE_DIR / "schema")
    args = parser.parse_args(argv)

    if args.cmd == "schema":
        for path in export_json_schema(args.out):
            print(f"wrote {path}")
        return 0
    try:
        kb = load_knowledge(args.dir)
    except KnowledgeError as exc:
        print(f"{len(exc.problems)} problem(s):", file=sys.stderr)
        for problem in exc.problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print(f"ok: {len(kb.jurisdictions)} jurisdictions, {len(kb.licenses)} licences, "
          f"{len(kb.citations)} citations, {len(kb.facilitators)} facilitators")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
