#!/usr/bin/env python3
"""
Backfill/normalize pgvector dimensions in Postgres.

Typical use:
- Mixed embeddings from OpenAI (1536) and Voyage (3072)
- Single target dimension in DB (usually 3072)
- Pad shorter vectors with trailing zeros

IMPORTANT:
- Your target pgvector column type must support target dim (e.g., vector(3072)).
- If your column is vector(1536), you cannot store 3072 vectors there.

Examples:
  export DATABASE_URL='postgresql://...'
  python scripts/backfill_pgvector_dims.py \
    --table memory_items \
    --id-column id \
    --embedding-column embedding \
    --target-dim 3072 \
    --batch-size 500

  # dry run
  python scripts/backfill_pgvector_dims.py ... --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import List, Tuple

try:
    import psycopg
except Exception as e:  # pragma: no cover
    print("Missing dependency: psycopg (pip install psycopg[binary])", file=sys.stderr)
    raise


IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def q_ident(name: str) -> str:
    if not IDENT_RE.match(name):
        raise ValueError(f"Unsafe identifier: {name!r}")
    return f'"{name}"'


def normalize(vec: List[float], target_dim: int, truncate: bool = False) -> Tuple[List[float], bool]:
    n = len(vec)
    if n == target_dim:
        return vec, False
    if n < target_dim:
        return vec + [0.0] * (target_dim - n), True
    if not truncate:
        raise ValueError(
            f"Vector has {n} dims, target is {target_dim}. "
            "Refusing to truncate without --truncate."
        )
    return vec[:target_dim], True


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backfill pgvector dimensions")
    p.add_argument("--database-url", default=os.getenv("DATABASE_URL"), help="Postgres URL (or use DATABASE_URL env)")
    p.add_argument("--table", required=True, help="Table containing embeddings")
    p.add_argument("--id-column", default="id", help="Primary key column")
    p.add_argument("--embedding-column", default="embedding", help="pgvector column")
    p.add_argument("--target-dim", type=int, default=3072)
    p.add_argument("--batch-size", type=int, default=500)
    p.add_argument("--where", default="", help="Optional SQL WHERE clause tail (no 'WHERE').")
    p.add_argument("--truncate", action="store_true", help="Allow truncation for vectors > target dim")
    p.add_argument("--dry-run", action="store_true", help="Print counts without writing")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if not args.database_url:
        print("Missing --database-url and DATABASE_URL env", file=sys.stderr)
        return 2

    table = q_ident(args.table)
    id_col = q_ident(args.id_column)
    emb_col = q_ident(args.embedding_column)
    where_sql = f" WHERE {args.where}" if args.where.strip() else ""

    scanned = 0
    changed = 0

    with psycopg.connect(args.database_url) as conn:
        with conn.cursor() as cur:
            # Filter out nulls; use vector_dims to limit to non-target rows only
            select_sql = (
                f"SELECT {id_col}, {emb_col}::text "
                f"FROM {table} "
                f"WHERE {emb_col} IS NOT NULL "
                f"AND vector_dims({emb_col}) <> %s"
            )
            if where_sql:
                # add caller-provided predicate safely as raw tail after own WHERE
                select_sql += f" AND ({args.where})"

            cur.execute(select_sql, (args.target_dim,))

            while True:
                rows = cur.fetchmany(args.batch_size)
                if not rows:
                    break

                updates = []
                for row_id, emb_text in rows:
                    scanned += 1
                    vec = json.loads(emb_text)
                    norm, did_change = normalize(vec, args.target_dim, truncate=args.truncate)
                    if did_change:
                        changed += 1
                        if not args.dry_run:
                            updates.append((json.dumps(norm, separators=(",", ":")), row_id))

                if updates:
                    update_sql = f"UPDATE {table} SET {emb_col} = %s::vector WHERE {id_col} = %s"
                    cur.executemany(update_sql, updates)
                    conn.commit()

    print(
        json.dumps(
            {
                "scanned": scanned,
                "changed": changed,
                "dryRun": args.dry_run,
                "targetDim": args.target_dim,
                "table": args.table,
                "idColumn": args.id_column,
                "embeddingColumn": args.embedding_column,
            },
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
