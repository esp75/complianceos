"""Load Celestia framework YAML into theopenlane as Standards/Controls/Subcontrols.

    uv run python -m app.loaders.framework_loader

For each framework dir under ``layers/L1-substrate/frameworks/`` it:
  1. upserts a Standard from framework.yaml (createStandard),
  2. upserts one Control per article file (createControl, linked via standardID),
  3. upserts one Subcontrol per item in the article's spec.controls (createSubcontrol).

RASE / deontic / entity_links / severity carry through losslessly in descriptionJSON;
cross_references go to mappedCategories. Evidence types are reported but not pushed
(theopenlane has no first-class EvidenceType — they live as a BFF tag vocabulary, ADR-0012).

Idempotent: existing Standards/Controls/Subcontrols (matched by shortName/refCode) are
reused, so re-running does not duplicate.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

import httpx
import yaml

from app.loaders.schema import ControlDoc, FrameworkDoc

BASE = os.environ.get("CELESTIA_OPENLANE_BASE_URL", "http://localhost:17608")
PASSWORD = os.environ.get("CELESTIA_SEED_PASSWORD", "Cel3stia!Strong#Pass1")
OWNER = ("founder@celestia.eu", "Celestia", "Founder")
FRAMEWORKS_DIR = Path(
    os.environ.get(
        "CELESTIA_FRAMEWORKS_DIR",
        str(Path(__file__).resolve().parents[3] / "layers" / "L1-substrate" / "frameworks"),
    )
)


class LoaderError(RuntimeError):
    pass


async def gql(http: httpx.AsyncClient, token: str, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    resp = await http.post(
        f"{BASE}/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": query, "variables": variables},
    )
    payload = resp.json()
    if payload.get("errors"):
        raise LoaderError(f"GraphQL errors: {payload['errors']}")
    return payload.get("data") or {}


async def authenticate(http: httpx.AsyncClient) -> str:
    """Register+verify or login the bootstrap owner; return a bearer token.
    The client's cookie jar captures the session cookie GraphQL needs alongside the JWT.
    """
    email, first, last = OWNER
    reg = await http.post(
        f"{BASE}/v1/register",
        json={"first_name": first, "last_name": last, "email": email, "password": PASSWORD},
    )
    if reg.status_code in (200, 201) and reg.json().get("token"):
        ver = await http.get(f"{BASE}/v1/verify", params={"token": reg.json()["token"]})
        token = ver.json().get("access_token")
        if token:
            return str(token)
    login = await http.post(f"{BASE}/v1/login", json={"username": email, "password": PASSWORD})
    token = login.json().get("access_token")
    if not token:
        raise LoaderError(f"auth failed for {email}: {login.text}")
    return str(token)


async def upsert_standard(http: httpx.AsyncClient, token: str, fw: FrameworkDoc) -> str:
    m, s = fw.metadata, fw.spec
    short = m.short_name or m.name
    existing = await gql(
        http, token,
        "query($s:String!){ standards(where:{shortName:$s}){ edges{ node{ id } } } }",
        {"s": short},
    )
    edges = existing.get("standards", {}).get("edges", [])
    if edges:
        return str(edges[0]["node"]["id"])

    domains = s.scope.activity_types if s.scope else []
    data = await gql(
        http, token,
        "mutation($i:CreateStandardInput!){ createStandard(input:$i){ standard{ id } } }",
        {"i": {
            "name": m.display_name,
            "shortName": short,
            "framework": m.version,
            "description": s.description,
            "governingBody": m.governing_body,
            "domains": domains,
            "tags": [t for t in [m.jurisdiction, s.category] if t],
        }},
    )
    return str(data["createStandard"]["standard"]["id"])


async def existing_refcodes(
    http: httpx.AsyncClient, token: str, query: str, var: dict[str, Any], key: str
) -> set[str]:
    data = await gql(http, token, query, var)
    return {e["node"]["refCode"] for e in data.get(key, {}).get("edges", [])}


async def upsert_control(
    http: httpx.AsyncClient, token: str, std_id: str, ctrl: ControlDoc, seen: set[str]
) -> str | None:
    m, s = ctrl.metadata, ctrl.spec
    if m.citation in seen:
        # already present; find its id to attach subcontrols
        data = await gql(
            http, token,
            "query($id:ID!){ controls(where:{hasStandardWith:{id:$id}}){ edges{ node{ id refCode } } } }",
            {"id": std_id},
        )
        for e in data.get("controls", {}).get("edges", []):
            if e["node"]["refCode"] == m.citation:
                return str(e["node"]["id"])
        return None

    description_json: list[dict[str, Any]] = [{
        "rase": s.rase.model_dump(exclude_none=True) if s.rase else None,
        "deontic_modality": s.deontic_modality,
        "entity_links": [el.model_dump() for el in s.entity_links],
        "validation_status": m.validation_status,
        "celestia_name": m.name,
    }]
    data = await gql(
        http, token,
        "mutation($i:CreateControlInput!){ createControl(input:$i){ control{ id } } }",
        {"i": {
            "refCode": m.citation,
            "title": m.display_name,
            "description": s.description,
            "referenceFramework": m.framework,
            "standardID": std_id,
            "mappedCategories": s.cross_references,
            "descriptionJSON": description_json,
        }},
    )
    return str(data["createControl"]["control"]["id"])


async def upsert_subcontrols(http: httpx.AsyncClient, token: str, ctrl_id: str, ctrl: ControlDoc) -> int:
    seen = await existing_refcodes(
        http, token,
        "query($id:ID!){ subcontrols(where:{hasControlWith:{id:$id}}){ edges{ node{ id refCode } } } }",
        {"id": ctrl_id}, "subcontrols",
    )
    created = 0
    for sub in ctrl.spec.controls:
        if sub.id in seen:
            continue
        description_json: list[dict[str, Any]] = [{
            "severity": sub.severity,
            "evidence_required": sub.evidence_required,
            "assessment_frequency": sub.assessment_frequency,
            "verification_method": sub.verification_method,
            "breach_consequence": sub.breach_consequence,
        }]
        await gql(
            http, token,
            "mutation($i:CreateSubcontrolInput!){ createSubcontrol(input:$i){ subcontrol{ id } } }",
            {"i": {
                "refCode": sub.id,
                "title": sub.id,
                "description": sub.description,
                "controlID": ctrl_id,
                "descriptionJSON": description_json,
            }},
        )
        created += 1
    return created


def load_framework_dir(path: Path) -> tuple[FrameworkDoc, list[ControlDoc], int]:
    fw = FrameworkDoc.model_validate(yaml.safe_load((path / "framework.yaml").read_text()))
    controls_dir = (path / fw.spec.controls_path).resolve()
    controls = [
        ControlDoc.model_validate(yaml.safe_load(f.read_text()))
        for f in sorted(controls_dir.glob("*.yaml"))
    ]
    ev_count = 0
    if fw.spec.evidence_types_path:
        ev_file = (path / fw.spec.evidence_types_path).resolve()
        if ev_file.exists():
            ev = yaml.safe_load(ev_file.read_text()) or {}
            ev_count = len(ev.get("spec", {}).get("evidence_types", []))
    return fw, controls, ev_count


def discover_framework_dirs() -> list[Path]:
    if not FRAMEWORKS_DIR.is_dir():
        return []
    return sorted(d for d in FRAMEWORKS_DIR.iterdir() if (d / "framework.yaml").exists())


async def main() -> int:
    fw_dirs = discover_framework_dirs()
    if not fw_dirs:
        print(f"no frameworks found under {FRAMEWORKS_DIR}", file=sys.stderr)
        return 1
    print(f"Loading {len(fw_dirs)} frameworks from {FRAMEWORKS_DIR} into {BASE}\n")

    async with httpx.AsyncClient(timeout=30.0) as http:
        token = await authenticate(http)
        for d in fw_dirs:
            fw, controls, ev_count = load_framework_dir(d)
            std_id = await upsert_standard(http, token, fw)
            print(
                f"standard {fw.metadata.short_name:<12} = standard:{std_id}  "
                f"({len(controls)} controls, {ev_count} evidence types)"
            )

            seen_ctrl = await existing_refcodes(
                http, token,
                "query($id:ID!){ controls(where:{hasStandardWith:{id:$id}}){ edges{ node{ id refCode } } } }",
                {"id": std_id}, "controls",
            )
            n_ctrl = n_sub = 0
            for ctrl in controls:
                cid = await upsert_control(http, token, std_id, ctrl, seen_ctrl)
                if cid is None:
                    print(f"  ! could not resolve control {ctrl.metadata.citation}", file=sys.stderr)
                    continue
                if ctrl.metadata.citation not in seen_ctrl:
                    n_ctrl += 1
                n_sub += await upsert_subcontrols(http, token, cid, ctrl)
            print(f"  -> {n_ctrl} controls created, {n_sub} subcontrols created\n")

    print("done. Verify: standards{ name controls{ refCode title } }")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
