"""Trust store against a real Postgres (opt-in, THREAT_MODEL finding 1).

Concurrent signs for one org must produce a single linear chain, and the schema must refuse a
fork even when a writer skips the lock. Set COMPLIANCEOS_PG_TEST_DSN to a scratch database; each
run uses fresh org ids.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncIterator

import asyncpg
import pytest

from app.api.trust.store import TrustStore, chain_hash

PG_DSN = os.environ.get("COMPLIANCEOS_PG_TEST_DSN")


@pytest.fixture
async def trust() -> AsyncIterator[TrustStore]:
    if not PG_DSN:
        pytest.skip("set COMPLIANCEOS_PG_TEST_DSN to run the trust store contract")
    store = TrustStore(PG_DSN)
    await store.connect()
    await store.apply_schema()
    yield store
    await store.close()


def _org() -> str:
    return f"test-{uuid.uuid4().hex}"


@pytest.mark.asyncio
async def test_concurrent_appends_form_one_linear_chain(trust: TrustStore) -> None:
    org = _org()
    roots = [uuid.uuid4().bytes * 2 for _ in range(12)]
    results = await asyncio.gather(*(
        trust.append_next(org, root, b"sig" + root, "{}") for root in roots
    ))
    prevs = [prev for _, prev in results]
    assert prevs.count(None) == 1, "exactly one genesis bundle"
    assert len(set(prevs)) == len(prevs), "no two bundles share a predecessor"
    assert set(p for p in prevs if p is not None) <= set(roots)
    # Walk the chain from genesis: it visits every bundle once.
    successor = {prev: root for (_, prev), root in zip(results, roots, strict=True)}
    head, seen = None, 0
    while head in successor:
        head = successor[head]
        seen += 1
    assert seen == len(roots)
    assert await trust.last_root(org) == head


@pytest.mark.asyncio
async def test_chain_hash_is_stored(trust: TrustStore) -> None:
    org = _org()
    await trust.append_next(org, b"r1" * 16, b"s1", "{}")
    await trust.append_next(org, b"r2" * 16, b"s2", "{}")
    conn = await asyncpg.connect(PG_DSN)
    try:
        row = await conn.fetchrow(
            "SELECT prev_root, chain_hash FROM trust_bundle WHERE org_id = $1 ORDER BY id DESC "
            "LIMIT 1", org)
    finally:
        await conn.close()
    assert row["prev_root"] == b"r1" * 16
    assert row["chain_hash"] == chain_hash(b"r1" * 16, b"r2" * 16, b"s2")


@pytest.mark.asyncio
async def test_schema_refuses_a_fork_without_the_lock(trust: TrustStore) -> None:
    org = _org()
    await trust.append_bundle(org, b"g" * 32, None, b"h" * 32, b"s", "{}")
    with pytest.raises(asyncpg.UniqueViolationError):
        await trust.append_bundle(org, b"x" * 32, None, b"h" * 32, b"s", "{}")
    await trust.append_bundle(org, b"a" * 32, b"g" * 32, b"h" * 32, b"s", "{}")
    with pytest.raises(asyncpg.UniqueViolationError):
        await trust.append_bundle(org, b"b" * 32, b"g" * 32, b"h" * 32, b"s", "{}")
