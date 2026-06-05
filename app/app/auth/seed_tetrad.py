"""Seed the 4-role tetrad (operator / insurer / regulator / admin) for a demo org.

Run from the app dir against the local stack:

    uv run python -m app.auth.seed_tetrad

Realizes the tetrad on top of theopenlane's embedded OpenFGA model (ADR-0012):

  admin     -> org ADMIN membership
  operator  -> org MEMBER + Operators group, which is wired as
               evidence/control/standard creator on the org (group#member -> can_create_*)
  insurer   -> org MEMBER only (read; further scoping at the BFF)
  regulator -> org MEMBER + a direct audit_log_viewer tuple

theopenlane mutations are used where they exist; for grants it has no mutation for
(regulator audit_log_viewer) we write the FGA tuple directly to the same store.
Finally it runs OpenFGA checks proving the roles differ, and prints a PAT for the
owner so you can exercise the BFF (`GET /auth/me`, `GET /auth/can`).

Idempotent-ish: re-running reuses an existing user/org/group where it can.
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any, cast

import httpx

from app.clients.openfga import OpenFGAClient
from app.config import Settings

BASE = os.environ.get("CELESTIA_OPENLANE_BASE_URL", "http://localhost:17608")
OPENFGA_URL = os.environ.get("CELESTIA_OPENFGA_URL", "http://localhost:8080")
PASSWORD = os.environ.get("CELESTIA_SEED_PASSWORD", "Cel3stia!Strong#Pass1")

ORG_NAME = "Celestia Demo Operator"
OWNER = ("founder@celestia.eu", "Celestia", "Founder")
DEMO_USERS = {
    "operator": ("operator@celestia.eu", "Olive", "Operator"),
    "insurer": ("insurer@celestia.eu", "Ivan", "Insurer"),
    "regulator": ("regulator@celestia.eu", "Rita", "Regulator"),
    "admin": ("admin@celestia.eu", "Adam", "Admin"),
}
GROUPS = {
    "operator": "Operators",
    "insurer": "Insurers",
    "regulator": "Regulators",
    "admin": "Administrators",
}


class SeedError(RuntimeError):
    pass


async def gql(
    http: httpx.AsyncClient, token: str, query: str, variables: dict[str, Any] | None = None
) -> dict[str, Any]:
    resp = await http.post(
        f"{BASE}/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": query, "variables": variables or {}},
    )
    payload = resp.json()
    if payload.get("errors"):
        raise SeedError(f"GraphQL errors: {payload['errors']}")
    return cast("dict[str, Any]", payload.get("data", {}))


async def authenticate(http: httpx.AsyncClient, email: str, first: str, last: str) -> tuple[str, str]:
    """Register+verify (first run) or login (subsequent). Returns (token, user_id).
    The http client's cookie jar captures the session cookie that JWT GraphQL needs.
    """
    reg = await http.post(
        f"{BASE}/v1/register",
        json={"first_name": first, "last_name": last, "email": email, "password": PASSWORD},
    )
    if reg.status_code in (200, 201) and reg.json().get("token"):
        body = reg.json()
        ver = await http.get(f"{BASE}/v1/verify", params={"token": body["token"]})
        token = ver.json().get("access_token")
        if not token:
            raise SeedError(f"verify did not return access_token for {email}: {ver.text}")
        return str(token), str(body["user_id"])

    # Already registered -> login.
    login = await http.post(
        f"{BASE}/v1/login", json={"username": email, "password": PASSWORD}
    )
    token = login.json().get("access_token")
    if not token:
        raise SeedError(f"login failed for {email}: {login.text}")
    data = await gql(http, str(token), "{ self { id } }")
    return str(token), str(data["self"]["id"])


async def ensure_user(email: str, first: str, last: str) -> str:
    """Authenticate a demo user in its own session; return only its user id."""
    async with httpx.AsyncClient(timeout=20.0) as http:
        _token, uid = await authenticate(http, email, first, last)
        return uid


async def mint_user_pat(email: str, first: str, last: str, org_id: str) -> str:
    """Log the user in and mint a Personal Access Token scoped to the demo org,
    so the BFF (M4) can be exercised as this role with a standalone bearer.
    """
    async with httpx.AsyncClient(timeout=20.0) as http:
        token, _uid = await authenticate(http, email, first, last)
        data = await gql(
            http, token,
            "mutation($i:CreatePersonalAccessTokenInput!)"
            "{ createPersonalAccessToken(input:$i){ personalAccessToken{ token } } }",
            {"i": {"name": f"celestia-demo-{email.split('@')[0]}", "organizationIDs": [org_id]}},
        )
        return str(data["createPersonalAccessToken"]["personalAccessToken"]["token"])


async def find_or_create_org(http: httpx.AsyncClient, token: str) -> str:
    data = await gql(
        http,
        token,
        "query($n:String!){ organizations(where:{displayName:$n}){ edges{ node{ id name } } } }",
        {"n": ORG_NAME},
    )
    edges = data.get("organizations", {}).get("edges", [])
    if edges:
        return str(edges[0]["node"]["id"])
    data = await gql(
        http,
        token,
        "mutation($i:CreateOrganizationInput!){ createOrganization(input:$i){ organization{ id } } }",
        {"i": {"name": ORG_NAME, "displayName": ORG_NAME,
               "description": "Demo satellite operator for the Celestia tetrad seed."}},
    )
    return str(data["createOrganization"]["organization"]["id"])


async def find_or_create_group(http: httpx.AsyncClient, token: str, org_id: str, name: str) -> str:
    data = await gql(
        http,
        token,
        "query($org:ID!){ groups(where:{ownerID:$org}){ edges{ node{ id name } } } }",
        {"org": org_id},
    )
    for edge in data.get("groups", {}).get("edges", []):
        if edge["node"]["name"] == name:
            return str(edge["node"]["id"])
    data = await gql(
        http,
        token,
        "mutation($i:CreateGroupInput!){ createGroup(input:$i){ group{ id } } }",
        {"i": {"name": name, "ownerID": org_id, "description": f"{name} (tetrad role group)"}},
    )
    return str(data["createGroup"]["group"]["id"])


async def try_mutation(
    http: httpx.AsyncClient, token: str, query: str, variables: dict[str, Any], what: str
) -> bool:
    """Run a mutation, tolerating already-exists. Returns True on success/benign."""
    try:
        await gql(http, token, query, variables)
        return True
    except SeedError as exc:
        msg = str(exc).lower()
        if "already exists" in msg or "constraint" in msg or "duplicate" in msg:
            return True
        print(f"  ! {what} failed: {exc}", file=sys.stderr)
        return False


async def main() -> int:
    print(f"Seeding tetrad against {BASE} (FGA {OPENFGA_URL})\n")
    fga = OpenFGAClient(Settings(openfga_url=OPENFGA_URL), httpx.AsyncClient(timeout=20.0))

    async with httpx.AsyncClient(timeout=20.0) as owner_http:
        # 1. Owner + org
        owner_token, owner_id = await authenticate(owner_http, *OWNER)
        org_id = await find_or_create_org(owner_http, owner_token)
        print(f"owner {OWNER[0]} = user:{owner_id}")
        print(f"org   {ORG_NAME!r} = organization:{org_id}\n")

        # 2. Groups
        group_ids = {
            role: await find_or_create_group(owner_http, owner_token, org_id, name)
            for role, name in GROUPS.items()
        }
        for role, gid in group_ids.items():
            print(f"group {GROUPS[role]:<14} = group:{gid}")
        print()

        # 3. Wire the Operators group as evidence/control/standard creator on the org.
        await try_mutation(
            owner_http, owner_token,
            "mutation($id:ID!,$i:UpdateOrganizationInput!)"
            "{ updateOrganization(id:$id,input:$i){ organization{ id } } }",
            {"id": org_id, "i": {
                "addEvidenceCreatorIDs": [group_ids["operator"]],
                "addControlCreatorIDs": [group_ids["operator"]],
                "addStandardCreatorIDs": [group_ids["operator"]],
            }},
            "wire Operators as creator",
        )
        print("wired Operators group as evidence/control/standard creator\n")

        # 4. Demo users
        user_ids = {
            role: await ensure_user(*info) for role, info in DEMO_USERS.items()
        }
        for role, uid in user_ids.items():
            print(f"user  {role:<10} = user:{uid}")
        print()

        # 5. Memberships (org + group). Fall back to direct FGA tuples if a mutation
        #    is unavailable, so the demo is verifiable either way.
        for role, uid in user_ids.items():
            org_role = "ADMIN" if role == "admin" else "MEMBER"
            ok = await try_mutation(
                owner_http, owner_token,
                "mutation($i:CreateOrgMembershipInput!){ createOrgMembership(input:$i){ orgMembership{ id } } }",
                {"i": {"organizationID": org_id, "userID": uid, "role": org_role}},
                f"org membership {role}",
            )
            if not ok:
                fga_rel = "admin" if role == "admin" else "member"
                await fga.write_tuple(f"user:{uid}", fga_rel, f"organization:{org_id}")
                print(f"  -> fallback FGA tuple: user:{uid} {fga_rel} organization:{org_id}")

            ok = await try_mutation(
                owner_http, owner_token,
                "mutation($i:CreateGroupMembershipInput!){ createGroupMembership(input:$i){ groupMembership{ id } } }",
                {"i": {"groupID": group_ids[role], "userID": uid, "role": "MEMBER"}},
                f"group membership {role}",
            )
            if not ok:
                await fga.write_tuple(f"user:{uid}", "member", f"group:{group_ids[role]}")
                print(f"  -> fallback FGA tuple: user:{uid} member group:{group_ids[role]}")

        # 6. audit_log_viewer (no theopenlane mutation -> direct tuple). Celestia grants
        #    audit-log visibility to BOTH regulator and admin; org ADMIN alone does not
        #    inherit it in the upstream model (only owner does).
        for role in ("regulator", "admin"):
            await fga.write_tuple(
                f"user:{user_ids[role]}", "audit_log_viewer", f"organization:{org_id}"
            )
        print("\ngranted regulator + admin audit_log_viewer (direct tuples)\n")

        # 7. Owner PAT for BFF demo.
        pat = None
        try:
            data = await gql(
                owner_http, owner_token,
                "mutation($i:CreatePersonalAccessTokenInput!)"
                "{ createPersonalAccessToken(input:$i){ personalAccessToken{ token } } }",
                {"i": {"name": "celestia-demo", "organizationIDs": [org_id]}},
            )
            pat = data["createPersonalAccessToken"]["personalAccessToken"]["token"]
        except SeedError as exc:
            print(f"  ! could not mint owner PAT: {exc}", file=sys.stderr)

    # 8. Verify the tetrad via FGA checks.
    org = f"organization:{org_id}"
    matrix: list[tuple[str, str, bool]] = [
        ("operator", "can_create_evidence", True),
        ("operator", "audit_log_viewer", False),
        ("insurer", "can_create_evidence", False),
        ("insurer", "can_view", True),
        ("regulator", "audit_log_viewer", True),
        ("regulator", "can_create_evidence", False),
        ("admin", "can_create_evidence", True),
        ("admin", "audit_log_viewer", True),
    ]
    # can_view traverses the org's conditioned `access` tuple (email_domains_allowed),
    # so checks must supply the email_domain parameter. allowed_domains is [] (allow-all).
    ctx = {"email_domain": OWNER[0].split("@", 1)[1]}
    print("OpenFGA verification (role / relation / got / expected):")
    all_ok = True
    for role, relation, expected in matrix:
        got = await fga.check(f"user:{user_ids[role]}", relation, org, context=ctx)
        ok = got == expected
        all_ok = all_ok and ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {role:<10} {relation:<22} got={got!s:<5} expected={expected}")

    print(f"\norg: {org}")
    if pat:
        print(f"PAT owner {pat}")

    # 9. Mint a PAT per demo role (scoped to the org) for M4 BFF role testing.
    print("\ndemo PATs (BFF on :8001) — format: PAT <role> <token>")
    for role, info in DEMO_USERS.items():
        try:
            upat = await mint_user_pat(*info, org_id)
            print(f"PAT {role} {upat}")
        except SeedError as exc:
            print(f"  ! PAT mint failed for {role}: {exc}", file=sys.stderr)

    await fga._http.aclose()
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
