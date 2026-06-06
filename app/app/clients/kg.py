"""Async client to the L2 knowledge-graph Postgres (Postgres 17 + AGE + pgvector, ADR-0007).

The single integration surface for L2: pgvector ANN (LightRAG local level) + AGE Cypher
traversal (global level) + the Context Core provenance tables. Obligation ref_codes and
titles are trusted framework content (not user free-text), so Cypher string literals are
escaped defensively rather than parameterized through agtype.
"""

from __future__ import annotations

from typing import Any, cast

import asyncpg

from app.kg.embeddings import to_pgvector

_GRAPH = "celestia_kg"


class KGError(RuntimeError):
    """Raised on a KG transport error or when the KG is unreachable."""


def _cy_str(value: str) -> str:
    """Escape a string for safe inclusion as a Cypher single-quoted literal."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _unquote_agtype(value: Any) -> str:
    """AGE returns agtype string values wrapped in double quotes; strip them."""
    s = str(value)
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s


class KGClient:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    @staticmethod
    async def _init_conn(conn: asyncpg.Connection) -> None:
        # AGE must be loaded and ag_catalog on the search_path for every connection.
        # Avoid the "$user" token — asyncpg mis-scans the leading $ as a bind param.
        await conn.execute("LOAD 'age';")
        await conn.execute("SET search_path = ag_catalog, public;")

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(
            self._dsn, min_size=1, max_size=5, init=self._init_conn
        )

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    def _require_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise KGError("KG pool not connected")
        return self._pool

    async def ping(self) -> bool:
        if self._pool is None:
            return False
        try:
            async with self._pool.acquire() as conn:
                return bool(await conn.fetchval("SELECT 1") == 1)
        except (asyncpg.PostgresError, OSError):
            return False

    async def apply_schema(self, schema_sql: str) -> None:
        async with self._require_pool().acquire() as conn:
            await conn.execute(schema_sql)

    # --- L2 vector index (LightRAG local level) ---

    async def upsert_obligation_embedding(
        self, ref_code: str, framework: str, content: str, embedding: list[float]
    ) -> None:
        async with self._require_pool().acquire() as conn:
            await conn.execute(
                "INSERT INTO obligation_embedding (ref_code, framework, content, embedding) "
                "VALUES ($1, $2, $3, $4::vector) "
                "ON CONFLICT (ref_code) DO UPDATE SET "
                "framework = EXCLUDED.framework, content = EXCLUDED.content, embedding = EXCLUDED.embedding",
                ref_code, framework, content, to_pgvector(embedding),
            )

    async def search_obligations(self, query_embedding: list[float], limit: int = 5) -> list[dict[str, Any]]:
        async with self._require_pool().acquire() as conn:
            rows = await conn.fetch(
                "SELECT ref_code, framework, content, (embedding <=> $1::vector) AS distance "
                "FROM obligation_embedding ORDER BY embedding <=> $1::vector LIMIT $2",
                to_pgvector(query_embedding), limit,
            )
        result: list[dict[str, Any]] = [dict(r) for r in rows]
        return result

    async def count_obligations(self) -> int:
        async with self._require_pool().acquire() as conn:
            return cast("int", await conn.fetchval("SELECT count(*) FROM obligation_embedding"))

    async def fetch_obligations(self, ref_codes: list[str]) -> list[dict[str, Any]]:
        """Fetch obligation rows by ref_code (used to hydrate graph-expanded neighbors)."""
        if not ref_codes:
            return []
        async with self._require_pool().acquire() as conn:
            rows = await conn.fetch(
                "SELECT ref_code, framework, content FROM obligation_embedding WHERE ref_code = ANY($1)",
                ref_codes,
            )
        result: list[dict[str, Any]] = [dict(r) for r in rows]
        return result

    # --- L2 graph (AGE) ---

    async def _cypher(self, query: str, *, columns: str = "(r ag_catalog.agtype)") -> list[Any]:
        # Qualify ag_catalog.cypher + re-assert search_path on the acquired connection:
        # asyncpg's pool runs RESET ALL on release, which clears the init-set search_path.
        sql = f"SELECT * FROM ag_catalog.cypher('{_GRAPH}', $$ {query} $$) AS {columns};"
        async with self._require_pool().acquire() as conn:
            await conn.execute("SET search_path = ag_catalog, public;")
            rows: list[Any] = await conn.fetch(sql)
            return rows

    async def merge_obligation_node(
        self, ref_code: str, framework: str, title: str, deontic: str
    ) -> None:
        await self._cypher(
            f"MERGE (o:Obligation {{ref_code: '{_cy_str(ref_code)}'}}) "
            f"SET o.framework = '{_cy_str(framework)}', o.title = '{_cy_str(title)}', "
            f"o.deontic = '{_cy_str(deontic)}' RETURN o.ref_code"
        )

    async def merge_evidence_edge(self, ref_code: str, evidence_type: str, framework: str) -> None:
        await self._cypher(
            f"MERGE (e:EvidenceType {{name: '{_cy_str(evidence_type)}'}}) "
            f"SET e.framework = '{_cy_str(framework)}' RETURN e.name"
        )
        await self._cypher(
            f"MATCH (o:Obligation {{ref_code: '{_cy_str(ref_code)}'}}), "
            f"(e:EvidenceType {{name: '{_cy_str(evidence_type)}'}}) "
            f"MERGE (o)-[:REQUIRES_EVIDENCE]->(e) RETURN o.ref_code"
        )

    async def merge_cites_edge(self, ref_code: str, cites_ref: str) -> None:
        await self._cypher(
            f"MATCH (o:Obligation {{ref_code: '{_cy_str(ref_code)}'}}) "
            f"MERGE (t:Obligation {{ref_code: '{_cy_str(cites_ref)}'}}) "
            f"MERGE (o)-[:CITES]->(t) RETURN o.ref_code"
        )

    async def cited_neighbors(self, ref_codes: list[str]) -> list[str]:
        """Global-level traversal: obligations CITES-linked from the seed set."""
        if not ref_codes:
            return []
        joined = ", ".join(f"'{_cy_str(rc)}'" for rc in ref_codes)
        rows = await self._cypher(
            f"MATCH (o:Obligation)-[:CITES]->(n:Obligation) "
            f"WHERE o.ref_code IN [{joined}] RETURN n.ref_code"
        )
        return [_unquote_agtype(r["r"]) for r in rows]

    async def evidence_types_for(self, ref_codes: list[str]) -> list[str]:
        if not ref_codes:
            return []
        joined = ", ".join(f"'{_cy_str(rc)}'" for rc in ref_codes)
        rows = await self._cypher(
            f"MATCH (o:Obligation)-[:REQUIRES_EVIDENCE]->(e:EvidenceType) "
            f"WHERE o.ref_code IN [{joined}] RETURN e.name"
        )
        return [_unquote_agtype(r["r"]) for r in rows]

    # --- Context Cores (provenance) ---

    async def insert_context_core(
        self, draft_id: str, source_type: str, source_ref: str, derivation: str
    ) -> None:
        async with self._require_pool().acquire() as conn:
            await conn.execute(
                "INSERT INTO context_core (draft_id, source_type, source_ref, derivation) "
                "VALUES ($1, $2, $3, $4)",
                draft_id, source_type, source_ref, derivation,
            )

    async def fetch_context_cores(self, draft_id: str) -> list[dict[str, Any]]:
        async with self._require_pool().acquire() as conn:
            rows = await conn.fetch(
                "SELECT draft_id, source_type, source_ref, derivation, created_at "
                "FROM context_core WHERE draft_id = $1 ORDER BY id",
                draft_id,
            )
        result: list[dict[str, Any]] = [dict(r) for r in rows]
        return result
