"""Pydantic models for the Celestia ``openlane.io/v1`` framework YAML schema.

Validates the hand-authored manifests under ``layers/L1-substrate/frameworks/``
before the loader transforms them into theopenlane mutations. Unknown keys are
ignored (pydantic v2 default) so the YAML can carry extra metadata without breaking
the loader; required fields are enforced.
"""

from __future__ import annotations

from pydantic import BaseModel


class Rase(BaseModel):
    """Requirement / Applicability / Selection / Exception annotation (ADR-0008)."""

    requirement: str | None = None
    applicability: str | None = None
    selection: str | None = None
    exception: str | None = None


class SubControl(BaseModel):
    """An item under a Control's ``spec.controls`` — maps to a theopenlane Subcontrol."""

    id: str
    description: str
    severity: str | None = None
    evidence_required: list[str] = []
    assessment_frequency: str | None = None
    verification_method: str | None = None
    breach_consequence: str | None = None


class EntityLink(BaseModel):
    entity: str
    relation: str


class ControlMeta(BaseModel):
    name: str
    framework: str
    citation: str
    display_name: str
    validation_status: str | None = None


class ControlSpec(BaseModel):
    description: str
    rase: Rase | None = None
    deontic_modality: str | None = None
    controls: list[SubControl] = []
    cross_references: list[str] = []
    entity_links: list[EntityLink] = []


class ControlDoc(BaseModel):
    apiVersion: str
    kind: str
    metadata: ControlMeta
    spec: ControlSpec


class Scope(BaseModel):
    territory: str | None = None
    activity_types: list[str] = []
    actor_types: list[str] = []


class FrameworkMeta(BaseModel):
    name: str
    display_name: str
    short_name: str | None = None
    version: str | None = None
    jurisdiction: str | None = None
    governing_body: str | None = None
    citation_pattern: str | None = None


class FrameworkXref(BaseModel):
    framework: str
    relation: str | None = None
    context: str | None = None


class FrameworkSpec(BaseModel):
    description: str
    category: str | None = None
    scope: Scope | None = None
    controls_path: str
    cross_references: list[FrameworkXref] = []
    evidence_types_path: str | None = None
    default_severity: str | None = None
    validation_status: str | None = None


class FrameworkDoc(BaseModel):
    apiVersion: str
    kind: str
    metadata: FrameworkMeta
    spec: FrameworkSpec
