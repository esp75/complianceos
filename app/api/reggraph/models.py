"""Pydantic v2 models for the reg-graph obligation corpus.

Source of truth for the shape of regulations/*.yaml. regulations/schema.yaml is
the human-readable view and must be kept in sync with this module.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Sector (1 digit) + year (4) + document type (1-2 letters, e.g. R, L, PC) + number (4),
# optional "(NN)" suffix for corrigenda/versions. Examples: 32024R1689, 52025PC0335.
CELEX_RE = re.compile(r"^[1-9][0-9]{4}[A-Z]{1,2}[0-9]{4}(\([0-9]{2}\))?$")
OBLIGATION_ID_RE = re.compile(r"^[A-Z0-9]+(-[A-Z0-9]+)*$")


class Source(StrEnum):
    EU_SPACE_ACT = "eu_space_act"
    FCC_22_74 = "fcc_22_74"
    ITU_FILINGS = "itu_filings"
    ISO_24113 = "iso_24113"


class Applicability(StrEnum):
    OPERATOR = "operator"
    MANUFACTURER = "manufacturer"
    LAUNCH_PROVIDER = "launch_provider"
    GROUND_SEGMENT = "ground_segment"


class ReviewStatus(StrEnum):
    DRAFT = "draft"
    AUTHOR_REVIEWED = "author_reviewed"
    LAWYER_REVIEWED = "lawyer_reviewed"


class EdgeType(StrEnum):
    """Edge types. Each maps to an Apache AGE edge label of the same name, upper-cased."""

    IMPLEMENTS = "implements"
    CONFLICTS_WITH = "conflicts_with"
    CITED_BY = "cited_by"
    DEPENDS_ON = "depends_on"
    SUPERSEDES = "supersedes"
    REFERENCES = "references"

    @property
    def age_label(self) -> str:
        return self.value.upper()


class Citation(BaseModel):
    """Pinpoint reference to the regulatory text an obligation rests on.

    kind=celex requires a CELEX number and is verified against EUR-Lex.
    Other kinds carry a url or document id and are verified manually.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["celex", "fcc_cfr", "itu_rr", "iso"]
    celex: str | None = None
    document_id: str | None = None
    article: str
    paragraph: str | None = None
    point: str | None = None
    url: str | None = None
    consolidated_date: date | None = None
    verified_at: datetime | None = None
    verified_by: Literal["eurlex_mcp", "manual"] | None = None

    @model_validator(mode="after")
    def _check_identifiers(self) -> Citation:
        if self.kind == "celex":
            if not self.celex or not CELEX_RE.match(self.celex):
                raise ValueError(f"kind=celex needs a valid CELEX number, got {self.celex!r}")
        elif not (self.document_id or self.url):
            raise ValueError(f"kind={self.kind} needs document_id or url")
        if self.verified_at is not None and self.verified_by is None:
            raise ValueError("verified_at set without verified_by")
        return self


class Obligation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=OBLIGATION_ID_RE.pattern)
    source: Source
    jurisdiction: str = Field(description="ISO-3166 alpha-2, 'EU' or 'INTERNATIONAL'")
    article: str
    text: str = Field(min_length=1, description="Paraphrase or verbatim obligation text")
    rationale_code: str = Field(description="Must exist in rationale_codes.yaml")
    effective_date: date
    valid_to: date | None = None
    applicability: list[Applicability] = Field(min_length=1)
    citation: Citation
    review_status: ReviewStatus = ReviewStatus.DRAFT

    applies_when: str | None = Field(default=None, description="Applicability DSL expression")
    evidence_required: dict[str, object] | None = Field(
        default=None, description="JSON-schema fragment describing required evidence"
    )
    retention_years: int | None = Field(default=None, ge=0)
    response_window: str | None = None
    authority: str | None = None

    supersedes: list[str] = Field(default_factory=list)
    superseded_by: str | None = None
    references: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_dates(self) -> Obligation:
        if self.valid_to is not None and self.valid_to < self.effective_date:
            raise ValueError("valid_to is before effective_date")
        return self


class ObligationFile(BaseModel):
    """Top-level shape of one regulations/<name>.yaml file."""

    model_config = ConfigDict(extra="forbid")

    source: Source
    jurisdiction: str
    obligations: list[Obligation] = Field(default_factory=list)


class RationaleCode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str


class RationaleCodes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codes: dict[str, RationaleCode]
