"""Hashing trick bag-of-words embedder."""

from __future__ import annotations

import math

from .tokenize import tokenize


class HashingEmbedder:
    def __init__(self, dim: int = 1024) -> None:
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        tokens = tokenize(text)
        vec = [0.0] * self.dim
        if not tokens:
            return vec
        for token in tokens:
            idx = hash(token) % self.dim
            vec[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            return vec
        return [v / norm for v in vec]
