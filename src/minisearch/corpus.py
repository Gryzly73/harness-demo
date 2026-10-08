"""Document model and JSONL corpus loading."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Document:
    id: str
    text: str
    lang: str = "en"


def load_jsonl(path: str | Path) -> list[Document]:
    docs: list[Document] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            docs.append(
                Document(id=row["id"], text=row["text"], lang=row.get("lang", "en"))
            )
    return docs
