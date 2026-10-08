# SPEC: minisearch (greenfield)

## Goal
Build a tiny search library over short texts (English and Russian) from scratch.
Standard library only at runtime. No network, no model files. Python 3.10+.
Quality is **measured**, not asserted: `python -m minisearch.evaluate`.

## Package contract (`src/minisearch/`)
`__init__.py` must export: `Document`, `HashingEmbedder`, `Index`, `load_jsonl`.

| Module | Contract |
|---|---|
| `corpus.py` | `Document(id: str, text: str, lang: str = "en")` frozen dataclass. `load_jsonl(path) -> list[Document]` reads `{"id","text","lang"}` per line (UTF-8, blank lines skipped). |
| `tokenize.py` | `tokenize(text: str) -> list[str]`: lowercase, split into word tokens. |
| `embed.py` | `HashingEmbedder(dim: int = 1024)` with `.dim` and `.embed(text) -> list[float]`: bag-of-words hashing trick, **unit length**, all-zero vector for text without tokens. |
| `index.py` | `Index(embedder)` with `.add(doc)`, `.add_many(docs)`, `.search(query, k=5) -> list[tuple[Document, float]]` by cosine similarity, best first, ties by doc id, only scores > 0. |
| `cli.py` | `python -m minisearch.cli search QUERY [--corpus F] [-k N]`; default corpus `data/corpus.jsonl`. One line per hit: `<doc_id>\t<score:.3f>\t<first 60 chars of text>`. |
| `evaluate.py` | **Provided, protected.** Imports `Index`, `HashingEmbedder`, `load_jsonl` and the corpus path. Do not edit. |

## Features, in the order the plan should deliver them
1. **Core**: everything in the table above. English recall@3 >= 0.8 on `eval/en.jsonl`.
2. **Persistence**: `Index.save(path)`, `Index.load(path, embedder)`; CLI `index --corpus F --out P` and `search Q --index P`. An index built in one process must be searchable from another.
3. **Russian**: recall@3 >= 0.9 on `eval/ru.jsonl`, English must not regress (>= 0.8).
4. **Language filter**: `Index.search(query, k, lang=None)` and CLI `--lang`.

## Global acceptance (every iteration, `make check`)
`ruff check .` clean, `pytest -q` green, `python -m minisearch.evaluate --set en --min-recall 0.8`.

## Oracle (humans wrote it, the agent may not touch it)
`tests/acceptance/`, `eval/`, `data/`, `SPEC.md`, `src/minisearch/evaluate.py`, `harness/`, `loop.sh`, `.cursor/`.
The plan must make every file in `tests/acceptance/` the `done when` of some task.
