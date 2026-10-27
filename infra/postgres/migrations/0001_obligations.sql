-- Relational mirror of the reg-graph obligation records (regulations/*.yaml).
-- The AGE graph (reg_graph) holds the edges; this table holds the queryable rows.
-- Row-level security is NOT in this file. Policies belong under app/api/rls/,
-- which is reserved for external review (see CLAUDE.md).

CREATE TABLE IF NOT EXISTS obligations (
    id              text PRIMARY KEY,
    source          text NOT NULL CHECK (source IN ('eu_space_act','fcc_22_74','itu_filings','iso_24113')),
    jurisdiction    text NOT NULL,
    article         text NOT NULL,
    text            text NOT NULL,
    rationale_code  text NOT NULL,
    effective_date  date NOT NULL,
    valid_to        date,
    review_status   text NOT NULL DEFAULT 'draft'
                    CHECK (review_status IN ('draft','author_reviewed','lawyer_reviewed')),
    citation        jsonb NOT NULL,
    CHECK (valid_to IS NULL OR valid_to >= effective_date)
);

CREATE INDEX IF NOT EXISTS obligations_source_idx ON obligations (source, id);
