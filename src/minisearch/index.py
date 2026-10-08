"""In-memory cosine similarity index."""

from __future__ import annotations

import json
from pathlib import Path

from .corpus import Document
from .embed import HashingEmbedder


class Index:
    def __init__(self, embedder: HashingEmbedder) -> None:
        self._embedder = embedder
        self._docs: list[Document] = []
        self._vectors: list[list[float]] = []

    def add(self, doc: Document) -> None:
        self._docs.append(doc)
        self._vectors.append(self._embedder.embed(doc.text))

    def add_many(self, docs: list[Document]) -> None:
        for doc in docs:
            self.add(doc)

    def search(
        self, query: str, k: int = 5, lang: str | None = None
    ) -> list[tuple[Document, float]]:
        q = self._embedder.embed(query)
        scored: list[tuple[Document, float]] = []
        for doc, vec in zip(self._docs, self._vectors, strict=True):
            if lang is not None and doc.lang != lang:
                continue
            score = sum(a * b for a, b in zip(q, vec, strict=True))
            if score > 0:
                scored.append((doc, score))
        scored.sort(key=lambda item: (-item[1], item[0].id))
        return scored[:k]

    def save(self, path: str | Path) -> None:
        payload = {
            "docs": [
                {"id": d.id, "text": d.text, "lang": d.lang} for d in self._docs
            ]
        }
        Path(path).write_text(json.dumps(payload), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path, embedder: HashingEmbedder) -> Index:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        index = cls(embedder)
        for row in payload["docs"]:
            index.add(
                Document(id=row["id"], text=row["text"], lang=row.get("lang", "en"))
            )
        return index
