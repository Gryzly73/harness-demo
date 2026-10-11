"""Evaluate minisearch against an arbitrary JSONL corpus and labelled query set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from minisearch import HashingEmbedder, Index, load_jsonl


def load_queries(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--lang", choices=("ru", "en"))
    parser.add_argument("-k", type=int, default=3)
    parser.add_argument("--min-recall", type=float, default=0.0)
    args = parser.parse_args()

    index = Index(HashingEmbedder())
    index.add_many(load_jsonl(args.corpus))
    queries = load_queries(args.queries)

    hits = 0
    for item in queries:
        found = {
            document.id
            for document, _score in index.search(
                item["query"], k=args.k, lang=args.lang
            )
        }
        expected = set(item["relevant"])
        matched = bool(found & expected)
        hits += matched
        print(
            f"{'PASS' if matched else 'FAIL'}\t{item['query']}\t"
            f"expected={sorted(expected)}\tfound={sorted(found)}"
        )

    recall = hits / len(queries) if queries else 0.0
    language = args.lang or "all"
    print(
        f"recall@{args.k} [{language}] = {recall:.3f} "
        f"(min {args.min_recall:.3f})"
    )
    return 0 if recall >= args.min_recall else 1


if __name__ == "__main__":
    raise SystemExit(main())
