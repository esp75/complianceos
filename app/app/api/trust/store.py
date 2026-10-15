# MARKED-FOR-EXTERNAL-REVIEW — Trail of Bits / Quarkslab / Cure53
"""Trust store — tamper-evident bundle/audit chain persistence (Phase 4, ADR-0016).

A thin asyncpg surface over the same Postgres as the L2 KG (its own pool from ``trust_dsn``, no AGE).
Two tables: ``trust_org_key`` records each org's published Ed25519 public key + fingerprint, and
``trust_bundle`` is an append-only log where every signed bundle links to the previous bundle's
Merkle root via ``chain_hash = sha256(prev_root || merkle_root || signature)`` — so the sequence of
issued bundles per org is tamper-evident. Lifecycle mirrors ``KGClient``; wired tolerantly in the
lifespan and gated by ``require_trust``.
"""

from __future__ import annotations

from typing import cast

import asyncpg

TRUST_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS trust_org_key (
    org_id      TEXT PRIMARY KEY,
    public_key  BYTEA NOT NULL,
    fingerprint TEXT  NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS trust_bundle (
    id          BIGSERIAL PRIMARY KEY,
    org_id      TEXT NOT NULL,
    merkle_root BYTEA NOT NULL,
    prev_root   BYTEA,
    chain_hash  BYTEA NOT NULL,
    signature   BYTEA NOT NULL,
    manifest    JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS trust_bundle_org_idx ON trust_bundle (org_id, id);
"""


class TrustStoreError(RuntimeError):
    """Raised on a trust-store transport error or when the store is unreachable."""


class TrustStore:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=5)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    def _require_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise TrustStoreError("trust store pool not connected")
        return self._pool

    async def ping(self) -> bool:
        if self._pool is None:
            return False
        try:
            async with self._pool.acquire() as conn:
                return bool(await conn.fetchval("SELECT 1") == 1)
        except (asyncpg.PostgresError, OSError):
            return False

    async def apply_schema(self) -> None:
        async with self._require_pool().acquire() as conn:
            await conn.execute(TRUST_SCHEMA_SQL)

    async def upsert_org_key(self, org_id: str, public_key: bytes, fingerprint: str) -> None:
        async with self._require_pool().acquire() as conn:
            await conn.execute(
                "INSERT INTO trust_org_key (org_id, public_key, fingerprint) VALUES ($1, $2, $3) "
                "ON CONFLICT (org_id) DO UPDATE SET "
                "public_key = EXCLUDED.public_key, fingerprint = EXCLUDED.fingerprint",
                org_id, public_key, fingerprint,
            )

    async def last_root(self, org_id: str) -> bytes | None:
        """The Merkle root of the most recent bundle for ``org_id`` (the chain head)."""
        async with self._require_pool().acquire() as conn:
            row = await conn.fetchval(
                "SELECT merkle_root FROM trust_bundle WHERE org_id = $1 ORDER BY id DESC LIMIT 1",
                org_id,
            )
        return cast("bytes | None", row)

    async def append_bundle(
        self,
        org_id: str,
        merkle_root: bytes,
        prev_root: bytes | None,
        chain_hash: bytes,
        signature: bytes,
        manifest: str,
    ) -> int:
        """Append a signed bundle to the chain. ``manifest`` is canonical JSON text. Returns row id."""
        async with self._require_pool().acquire() as conn:
            row_id = await conn.fetchval(
                "INSERT INTO trust_bundle "
                "(org_id, merkle_root, prev_root, chain_hash, signature, manifest) "
                "VALUES ($1, $2, $3, $4, $5, $6::jsonb) RETURNING id",
                org_id, merkle_root, prev_root, chain_hash, signature, manifest,
            )
        return cast("int", row_id)
