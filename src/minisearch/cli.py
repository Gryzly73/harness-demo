"""Command-line interface for minisearch."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

from .corpus import Document, load_jsonl
from .embed import HashingEmbedder
from .index import Index

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = ROOT / "data" / "corpus.jsonl"


def _format_hit(doc_id: str, score: float, text: str) -> str:
    return f"{doc_id}\t{score:.3f}\t{text[:60]}"


def _records(hits: list[tuple[Document, float]]) -> list[dict[str, object]]:
    return [
        {"id": doc.id, "score": score, "text": doc.text, "lang": doc.lang}
        for doc, score in hits
    ]


def _render(hits: list[tuple[Document, float]], fmt: str) -> str:
    if fmt == "text":
        return "".join(
            _format_hit(doc.id, score, doc.text) + "\n" for doc, score in hits
        )
    if fmt == "json":
        return json.dumps(_records(hits), ensure_ascii=False) + "\n"
    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["id", "score", "text", "lang"])
        writer.writeheader()
        for row in _records(hits):
            writer.writerow(row)
        return buf.getvalue()
    raise ValueError(f"unknown format: {fmt}")


def cmd_search(args: argparse.Namespace) -> int:
    if args.index:
        index = Index.load(args.index, HashingEmbedder())
    else:
        index = Index(HashingEmbedder())
        index.add_many(load_jsonl(args.corpus))
    hits = index.search(args.query, k=args.k, lang=args.lang)
    payload = _render(hits, args.format)
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    index = Index(HashingEmbedder())
    index.add_many(load_jsonl(args.corpus))
    index.save(args.out)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="minisearch.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    search_p = sub.add_parser("search", help="search a corpus")
    search_p.add_argument("query")
    search_p.add_argument("--corpus", "-c", default=str(DEFAULT_CORPUS))
    search_p.add_argument("--index", default=None)
    search_p.add_argument("-k", type=int, default=5)
    search_p.add_argument("--lang", default=None)
    search_p.add_argument(
        "--format",
        choices=("text", "json", "csv"),
        default="text",
    )
    search_p.add_argument("--output", default=None)

    index_p = sub.add_parser("index", help="build and save an index")
    index_p.add_argument("--corpus", "-c", default=str(DEFAULT_CORPUS))
    index_p.add_argument("--out", required=True)

    args = parser.parse_args(argv)
    if args.command == "search":
        return cmd_search(args)
    if args.command == "index":
        return cmd_index(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
