---
name: openbrain-pgvector-search
description: Semantic retrieval for knowledge stored in OpenBrain Postgres databases using pgvector. Use when a user asks for meaning-based search (not keyword), context retrieval, or pgvector query/index troubleshooting.
---

# OpenBrain Pgvector Search

Run semantic search against OpenBrain-connected Postgres using `openbrain_tool` + `execute_sql`.

## Workflow

1. Run preflight SQL checks (extension + table/column discovery).
2. Confirm the embeddings table, vector column, content/title fields, and embedding dimension.
3. Run top-k semantic retrieval query.
4. Return concise results with score and source fields.
5. If retrieval is slow, recommend/create pgvector index pattern from `references/sql-patterns.md`.

## Required preflight checks

Use `openbrain_tool` with `execute_sql`.

- Check pgvector installed:
  - `select extname from pg_extension where extname='vector';`
- Find vector columns:
  - `select table_schema, table_name, column_name, udt_name from information_schema.columns where udt_name='vector' order by 1,2,3;`

If pgvector or vector columns are missing, stop and report exactly what is missing.

## Querying rules

- Use cosine distance unless user asks otherwise.
- Return top 5-10 hits by default.
- Include: `id`, `title` (if available), short content snippet, and similarity score.
- Do not fabricate embeddings. Use the embedding value/vector provided by user workflow/tooling.

## Output format

- One short header line.
- Bullet list of results with: title/id, similarity, short snippet.
- One final line with any blocker or next step.

## References

- SQL templates and indexing guidance: `references/sql-patterns.md`
