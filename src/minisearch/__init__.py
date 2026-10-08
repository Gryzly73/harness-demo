"""minisearch: tiny semantic-ish search over short texts."""

from .corpus import Document, load_jsonl
from .embed import HashingEmbedder
from .index import Index

__all__ = ["Document", "HashingEmbedder", "Index", "load_jsonl"]
