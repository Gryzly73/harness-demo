"""Result export contract (SPEC.md, feature 5).

DO NOT EDIT: protected by the harness.
"""

import csv
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "data" / "corpus.jsonl"


def run_search(*args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    return subprocess.run(
        [sys.executable, "-m", "minisearch.cli", "search", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )


def test_json_export_to_stdout_contains_complete_records():
    result = run_search(
        "grind size for espresso",
        "--corpus",
        str(CORPUS),
        "--lang",
        "en",
        "-k",
        "2",
        "--format",
        "json",
    )
    rows = json.loads(result.stdout)
    assert 1 <= len(rows) <= 2
    assert list(rows[0]) == ["id", "score", "text", "lang"]
    assert rows[0]["id"] == "en09"
    assert isinstance(rows[0]["score"], float)
    assert rows[0]["lang"] == "en"
    assert "Espresso" in rows[0]["text"]


def test_json_export_to_utf8_file_does_not_duplicate_stdout(tmp_path):
    output = tmp_path / "результат.json"
    result = run_search(
        "борщ со свёклой",
        "--corpus",
        str(CORPUS),
        "--lang",
        "ru",
        "--format",
        "json",
        "--output",
        str(output),
    )
    assert result.stdout == ""
    rows = json.loads(output.read_text(encoding="utf-8"))
    assert rows[0]["id"] == "ru13"
    assert "свёклой" in rows[0]["text"]


def test_csv_export_has_stable_header_and_parseable_scores(tmp_path):
    output = tmp_path / "results.csv"
    run_search(
        "grind size for espresso",
        "--corpus",
        str(CORPUS),
        "--lang",
        "en",
        "-k",
        "2",
        "--format",
        "csv",
        "--output",
        str(output),
    )
    with output.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
    assert reader.fieldnames == ["id", "score", "text", "lang"]
    assert rows[0]["id"] == "en09"
    assert float(rows[0]["score"]) > 0
    assert rows[0]["lang"] == "en"


def test_default_text_output_remains_backward_compatible():
    result = run_search(
        "grind size for espresso",
        "--corpus",
        str(CORPUS),
        "-k",
        "1",
    )
    columns = result.stdout.rstrip("\n").split("\t")
    assert columns[0] == "en09"
    assert len(columns) == 3
    assert len(columns[1].split(".")[1]) == 3
