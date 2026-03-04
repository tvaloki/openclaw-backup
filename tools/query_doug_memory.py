#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path

import psycopg2

DEFAULT_CONFIG = Path('/home/ec2-user/.openclaw/pgmemory.json')
SEMANTIC_SCRIPT = Path('/home/ec2-user/.openclaw/workspace/skills/pgmemory/scripts/query_memory.py')


def load_db_uri(config_path: Path) -> str:
    cfg = json.loads(config_path.read_text())
    return cfg['db']['uri']


def run_semantic(query: str, limit: int, config_path: Path) -> int:
    cmd = [
        'python3',
        str(SEMANTIC_SCRIPT),
        '--config',
        str(config_path),
        '--limit',
        str(limit),
        query,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode == 0:
        print(proc.stdout.strip())
    else:
        sys.stderr.write(proc.stderr)
    return proc.returncode


def run_fallback(query: str, limit: int, db_uri: str):
    conn = psycopg2.connect(db_uri)
    cur = conn.cursor()

    like = f"%{query}%"
    cur.execute(
        """
        select
          key,
          category,
          importance,
          left(content, 220) as snippet,
          created_at
        from public.memories
        where key ilike %s or content ilike %s
        order by importance desc, created_at desc
        limit %s
        """,
        (like, like, limit),
    )
    rows = cur.fetchall()

    if not rows:
        cur.execute(
            """
            select
              key,
              category,
              importance,
              left(content, 220) as snippet,
              greatest(
                similarity(coalesce(key,''), %s),
                similarity(content, %s)
              ) as sim,
              created_at
            from public.memories
            order by sim desc, importance desc, created_at desc
            limit %s
            """,
            (query, query, limit),
        )
        rows = cur.fetchall()
        print(f"Fallback (fuzzy) results for \"{query}\":")
        for key, category, importance, snippet, sim, created_at in rows:
            stars = '★' * int(importance) + '☆' * (3 - int(importance))
            print(f"- [{category}/{stars}] {key} (sim={sim:.3f})")
            print(f"  {snippet}")
    else:
        print(f"Fallback (keyword) results for \"{query}\":")
        for key, category, importance, snippet, created_at in rows:
            stars = '★' * int(importance) + '☆' * (3 - int(importance))
            print(f"- [{category}/{stars}] {key}")
            print(f"  {snippet}")

    cur.close()
    conn.close()


def main():
    ap = argparse.ArgumentParser(description='Query Doug memory with semantic search + SQL fallback')
    ap.add_argument('query', help='Query text')
    ap.add_argument('--limit', type=int, default=5)
    ap.add_argument('--config', default=str(DEFAULT_CONFIG))
    args = ap.parse_args()

    config_path = Path(args.config)

    rc = run_semantic(args.query, args.limit, config_path)
    if rc == 0:
        return

    print('\nSemantic query unavailable; using SQL fallback...')
    db_uri = load_db_uri(config_path)
    run_fallback(args.query, args.limit, db_uri)


if __name__ == '__main__':
    main()
