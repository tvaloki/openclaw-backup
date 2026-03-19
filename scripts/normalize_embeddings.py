#!/usr/bin/env python3
"""
Normalize embedding dimensions for a shared pgvector column.

Use case:
- OpenAI embeddings are 1536 dims
- Voyage embeddings are 3072 dims
- You want a single shared dimension (default here: 1536)

Behavior:
- If len(vec) < target_dim: right-pad with zeros
- If len(vec) > target_dim: truncate (optional, controlled by --truncate)
- If len(vec) == target_dim: unchanged

Examples:
  echo '[0.1, 0.2]' | python scripts/normalize_embeddings.py --target-dim 4
  python scripts/normalize_embeddings.py --input emb.json --output emb_norm.json --target-dim 1536
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List


def normalize(vec: List[float], target_dim: int, truncate: bool = False) -> List[float]:
    n = len(vec)
    if n == target_dim:
        return vec
    if n < target_dim:
        return vec + [0.0] * (target_dim - n)
    # n > target_dim
    if not truncate:
        raise ValueError(
            f"Vector has {n} dims, target is {target_dim}. "
            "Refusing to truncate without --truncate."
        )
    return vec[:target_dim]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Normalize embedding dimensions")
    p.add_argument("--input", help="Input JSON file (array of floats). If omitted, reads stdin.")
    p.add_argument("--output", help="Output JSON file. If omitted, writes stdout.")
    p.add_argument("--target-dim", type=int, default=3072, help="Target vector dimension (default: 3072)")
    p.add_argument(
        "--truncate",
        action="store_true",
        help="Allow truncation when input vector is larger than target",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    raw = None
    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            raw = json.load(f)
    else:
        raw = json.load(sys.stdin)

    if not isinstance(raw, list):
        raise TypeError("Input must be a JSON array of numbers")

    vec = [float(x) for x in raw]
    out = normalize(vec, target_dim=args.target_dim, truncate=not args.no_truncate)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(out, f, separators=(",", ":"))
    else:
        json.dump(out, sys.stdout, separators=(",", ":"))
        sys.stdout.write("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
