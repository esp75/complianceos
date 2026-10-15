"""Applicability rules: which licences a mission needs, and why (ADR-0018).

Evaluates the declarative ``applies_when`` rules from the knowledge pack against the facts of a
mission profile. No expression language and no ``eval``: a rule is a small tree of ``all`` /
``any`` / ``not`` / ``always`` nodes over field tests. Evaluation also collects the human
explanation of a match — the ``because`` text and citations of every branch that made it true —
which the roadmap shows as "why this applies to you".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.planner.knowledge import KnowledgeBase, License, Obligation, Rule
from app.planner.mission import MissionProfile


@dataclass(frozen=True)
class Reason:
    text: str
    cite: tuple[str, ...] = ()


@dataclass(frozen=True)
class Match:
    matched: bool
    reasons: tuple[Reason, ...] = field(default_factory=tuple)


def _test_field(rule: Rule, value: Any) -> bool:
    if rule.eq is not None:
        return value is not None and value == rule.eq
    if rule.in_ is not None:
        return value in rule.in_
    if rule.contains is not None:
        return rule.contains in (value or [])
    if rule.intersects is not None:
        return bool(set(value or []) & set(rule.intersects))
    if rule.gte is not None:
        return value is not None and value >= rule.gte
    if rule.lte is not None:
        return value is not None and value <= rule.lte
    if rule.present is not None:
        is_set = value is not None and value != [] and value != ""
        return is_set == rule.present
    raise ValueError(f"field rule on {rule.field!r} has no operator")  # unreachable: schema-checked


def _describe(rule: Rule) -> str:
    """Fallback explanation for a matched field test that has no ``because`` text."""
    label = (rule.field or "").replace("_", " ")
    if rule.contains is not None:
        return f"Your {label} include {rule.contains}."
    if rule.intersects is not None:
        return f"Your {label} include one of: {', '.join(rule.intersects)}."
    if rule.in_ is not None:
        return f"Your {label} is one of: {', '.join(rule.in_)}."
    if rule.gte is not None:
        return f"Your {label} is at least {rule.gte:g}."
    if rule.lte is not None:
        return f"Your {label} is at most {rule.lte:g}."
    if rule.present is not None:
        return f"Your {label} is {'set' if rule.present else 'not set'}."
    return f"Your {label} is {rule.eq}."


def _with_cites(reasons: tuple[Reason, ...], cite: list[str]) -> tuple[Reason, ...]:
    if not cite:
        return reasons
    return tuple(Reason(r.text, tuple(dict.fromkeys(r.cite + tuple(cite)))) for r in reasons)


def _explain(rule: Rule, children: tuple[Reason, ...]) -> tuple[Reason, ...]:
    """A node's own ``because`` (with its citations) comes first; a node that cites without
    explaining lends its citations to the reasons of the branches below it."""
    if rule.because:
        return (Reason(rule.because, tuple(rule.cite)),) + children
    return _with_cites(children, rule.cite)


def evaluate(rule: Rule, facts: dict[str, Any]) -> Match:
    """Evaluate ``rule`` and explain a match with the reasons of the branches that made it true."""
    if rule.always:
        return Match(True, _explain(rule, ()))
    if rule.field is not None:
        if not _test_field(rule, facts.get(rule.field)):
            return Match(False)
        if rule.because:
            return Match(True, _explain(rule, ()))
        return Match(True, (Reason(_describe(rule), tuple(rule.cite)),))
    if rule.not_ is not None:
        ok = not evaluate(rule.not_, facts).matched
        return Match(ok, _explain(rule, ()) if ok else ())
    if rule.all is not None:
        parts = [evaluate(r, facts) for r in rule.all]
        if not all(p.matched for p in parts):
            return Match(False)
        return Match(True, _explain(rule, tuple(r for p in parts for r in p.reasons)))
    if rule.any is not None:
        parts = [evaluate(r, facts) for r in rule.any]
        hits = [p for p in parts if p.matched]
        if not hits:
            return Match(False)
        return Match(True, _explain(rule, tuple(r for p in hits for r in p.reasons)))
    raise ValueError("empty rule")  # unreachable: schema-checked


def _dedupe(reasons: tuple[Reason, ...]) -> tuple[Reason, ...]:
    seen: dict[str, Reason] = {}
    for r in reasons:
        if r.text in seen:
            merged = tuple(dict.fromkeys(seen[r.text].cite + r.cite))
            seen[r.text] = Reason(r.text, merged)
        else:
            seen[r.text] = r
    return tuple(seen.values())


@dataclass(frozen=True)
class RequiredLicense:
    license: License
    reasons: tuple[Reason, ...]
    obligations: tuple[Obligation, ...]


def applicable_obligations(lic: License, facts: dict[str, Any]) -> tuple[Obligation, ...]:
    return tuple(
        o for o in lic.obligations
        if o.applies_when is None or evaluate(o.applies_when, facts).matched
    )


def required_licenses(kb: KnowledgeBase, mission: MissionProfile) -> list[RequiredLicense]:
    """Every licence whose rule matches the mission, ordered by jurisdiction then id."""
    facts = mission.facts()
    out = []
    for lic in sorted(kb.licenses.values(), key=lambda x: (x.jurisdiction, x.id)):
        m = evaluate(lic.applies_when, facts)
        if m.matched:
            out.append(RequiredLicense(lic, _dedupe(m.reasons), applicable_obligations(lic, facts)))
    return out
