"""Materialize the brownfield or greenfield demo overlay."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("brownfield", "greenfield"))
    parser.add_argument("--strip", action="store_true")
    args = parser.parse_args()

    overlay = ROOT / "modes" / args.mode
    if not overlay.is_dir():
        parser.error(f"missing overlay: {overlay}")

    if (ROOT / ".git").exists() and (ROOT / "SPEC.md").exists():
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        if status.strip():
            print("working tree has changes: commit or discard them first")
            return 1

    for relative in (
        "src",
        "tests/unit",
        "PLAN.md",
        "SPEC.md",
        "PROGRESS.md",
        "PLAN.proposed.md",
        "tests/acceptance/test_core.py",
        ".loop",
    ):
        remove(ROOT / relative)

    shutil.copytree(overlay, ROOT, dirs_exist_ok=True)
    (ROOT / ".loop").mkdir()
    if args.strip:
        for relative in ("modes", "demo", "DEMO.md"):
            remove(ROOT / relative)

    print(f"mode: {args.mode}")
    print("next: commit the materialized baseline, then run loop.ps1 or loop.sh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
