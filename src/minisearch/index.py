"""In-memory cosine similarity index."""

from __future__ import annotations

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

    def search(self, query: str, k: int = 5) -> list[tuple[Document, float]]:
        q = self._embedder.embed(query)
        scored: list[tuple[Document, float]] = []
        for doc, vec in zip(self._docs, self._vectors, strict=True):
            score = sum(a * b for a, b in zip(q, vec, strict=True))
            if score > 0:
                scored.append((doc, score))
        scored.sort(key=lambda item: (-item[1], item[0].id))
        return scored[:k]
