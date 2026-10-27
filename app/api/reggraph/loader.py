"""Load and cross-validate regulations/*.yaml into the reg-graph model.

Checks beyond per-field pydantic validation:
- obligation ids are unique across all files
- rationale_code exists in rationale_codes.yaml
- every id referenced by supersedes / superseded_by / references exists
- the supersedes relation is acyclic
- each file's source matches the source field on its obligations
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import yaml

from app.api.reggraph.models import Obligation, ObligationFile, RationaleCodes

OBLIGATION_FILES = (
    "eu_space_act.yaml",
    "fcc_22_74.yaml",
    "itu_filings.yaml",
    "iso_24113.yaml",
)


class CorpusError(ValueError):
    """Raised with every problem found, so one run reports the whole list."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("\n".join(problems))


def load_rationale_codes(path: Path) -> set[str]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return set(RationaleCodes.model_validate(raw).codes)


def load_corpus(regulations_dir: Path) -> list[Obligation]:
    codes = load_rationale_codes(regulations_dir / "rationale_codes.yaml")
    problems: list[str] = []
    obligations: list[Obligation] = []

    for name in OBLIGATION_FILES:
        path = regulations_dir / name
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        try:
            parsed = ObligationFile.model_validate(raw)
        except ValueError as exc:
            problems.append(f"{name}: {exc}")
            continue
        for ob in parsed.obligations:
            if ob.source != parsed.source:
                problems.append(f"{name}: {ob.id} has source {ob.source}, file is {parsed.source}")
            if ob.rationale_code not in codes:
                problems.append(f"{name}: {ob.id} unknown rationale_code {ob.rationale_code}")
        obligations.extend(parsed.obligations)

    problems.extend(check_graph(obligations))
    if problems:
        raise CorpusError(problems)
    return obligations


def check_graph(obligations: list[Obligation]) -> list[str]:
    problems: list[str] = []
    by_id: dict[str, Obligation] = {}
    for ob in obligations:
        if ob.id in by_id:
            problems.append(f"duplicate obligation id {ob.id}")
        by_id[ob.id] = ob

    for ob in obligations:
        for target in (*ob.supersedes, *ob.references, *([ob.superseded_by] if ob.superseded_by else [])):
            if target not in by_id:
                problems.append(f"{ob.id} points at unknown obligation {target}")

    problems.extend(_supersedes_cycles(by_id))
    return problems


def _supersedes_cycles(by_id: dict[str, Obligation]) -> list[str]:
    # Edge X -> Y means X supersedes Y. Detect any cycle with iterative DFS colouring.
    WHITE, GREY, BLACK = 0, 1, 2
    colour: dict[str, int] = defaultdict(int)
    problems: list[str] = []

    for start in by_id:
        if colour[start] != WHITE:
            continue
        stack: list[tuple[str, int]] = [(start, 0)]
        colour[start] = GREY
        while stack:
            node, idx = stack[-1]
            nexts = by_id[node].supersedes if node in by_id else []
            if idx < len(nexts):
                stack[-1] = (node, idx + 1)
                nxt = nexts[idx]
                if nxt not in by_id:
                    continue
                if colour[nxt] == GREY:
                    problems.append(f"supersedes cycle through {node} -> {nxt}")
                elif colour[nxt] == WHITE:
                    colour[nxt] = GREY
                    stack.append((nxt, 0))
            else:
                colour[node] = BLACK
                stack.pop()
    return problems
