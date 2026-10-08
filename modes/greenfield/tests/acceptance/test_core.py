"""Core contract (SPEC.md, feature 1).

DO NOT EDIT: protected by the harness.
"""

import os
import subprocess
import sys
from pathlib import Path

from minisearch import Document, HashingEmbedder, Index, load_jsonl
from minisearch.tokenize import tokenize

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "data" / "corpus.jsonl"


def test_tokenize_english():
    assert tokenize("Hello, World 42!") == ["hello", "world", "42"]


def test_embedding_has_dim_and_unit_length():
    emb = HashingEmbedder(dim=256)
    vec = emb.embed("sourdough bread starter")
    assert emb.dim == 256 and len(vec) == 256
    assert abs(sum(v * v for v in vec) - 1.0) < 1e-9


def test_text_without_tokens_gives_zero_vector():
    assert sum(HashingEmbedder().embed("!!!")) == 0.0


def test_load_jsonl_reads_the_corpus():
    docs = load_jsonl(CORPUS)
    assert len(docs) >= 30
    assert {d.lang for d in docs} == {"en", "ru"}
    assert all(isinstance(d, Document) and d.id and d.text for d in docs)


def test_search_ranks_relevant_doc_first():
    index = Index(HashingEmbedder())
    index.add(Document("a", "bread and flour and water"))
    index.add(Document("b", "black holes and gravity"))
    assert [d.id for d, _ in index.search("flour for bread", k=5)] == ["a"]


def test_search_respects_k_and_orders_by_score():
    index = Index(HashingEmbedder())
    index.add(Document("z", "water river lake bridge"))
    index.add(Document("x", "water"))
    index.add(Document("y", "water water river"))
    hits = index.search("water", k=2)
    assert [d.id for d, _ in hits] == ["x", "y"]
    assert hits[0][1] > hits[1][1]


def test_search_hides_zero_scores():
    index = Index(HashingEmbedder())
    index.add(Document("a", "black holes"))
    assert index.search("espresso") == []


def test_cli_search_output_format():
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    out = subprocess.run(
        [sys.executable, "-m", "minisearch.cli", "search", "grind size for espresso", "-k", "2"],
        capture_output=True,
        text=True,
        env=env,
        cwd=ROOT,
        check=True,
    ).stdout
    rows = [line.split("\t") for line in out.strip().splitlines()]
    assert 1 <= len(rows) <= 2 and all(len(r) == 3 for r in rows)
    assert rows[0][0] == "en09"
    assert len(rows[0][1].split(".")[1]) == 3
