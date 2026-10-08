"""Command-line interface for minisearch."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .corpus import load_jsonl
from .embed import HashingEmbedder
from .index import Index

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = ROOT / "data" / "corpus.jsonl"


def _format_hit(doc_id: str, score: float, text: str) -> str:
    return f"{doc_id}\t{score:.3f}\t{text[:60]}"


def cmd_search(args: argparse.Namespace) -> int:
    index = Index(HashingEmbedder())
    index.add_many(load_jsonl(args.corpus))
    for doc, score in index.search(args.query, k=args.k):
        print(_format_hit(doc.id, score, doc.text))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="minisearch.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    search_p = sub.add_parser("search", help="search a corpus")
    search_p.add_argument("query")
    search_p.add_argument("--corpus", "-c", default=str(DEFAULT_CORPUS))
    search_p.add_argument("-k", type=int, default=5)

    args = parser.parse_args(argv)
    if args.command == "search":
        return cmd_search(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
