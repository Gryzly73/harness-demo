#!/usr/bin/env bash
# Materialize one of the two demo modes into the working tree.
#   ./use_mode.sh brownfield   existing code + human-written plan (extend a project)
#   ./use_mode.sh greenfield   stubs + contract in SPEC.md, the AGENT writes the plan and the code
#   add --strip to delete modes/ and demo/ afterwards (use for the REAL run, so the agent
#   cannot read the reference solution; rehearse in a separate unstripped copy)
set -euo pipefail
cd "$(dirname "$0")"
mode="${1:-}"; strip="${2:-}"
[ -d "modes/${mode:-none}" ] || { echo "usage: $0 brownfield|greenfield [--strip]"; exit 2; }
if [ -d .git ] && [ -n "$(git status --porcelain)" ] && [ -f SPEC.md ]; then
  echo "working tree has changes: commit or discard them first"; exit 1
fi
rm -rf src tests/unit PLAN.md SPEC.md PROGRESS.md PLAN.proposed.md tests/acceptance/test_core.py .loop
cp -r "modes/$mode/." .
mkdir -p .loop
if [ "$strip" = "--strip" ]; then rm -rf modes demo DEMO.md; fi
echo "mode: $mode"
echo "next: git init -b main 2>/dev/null; git add -A && git commit -m baseline && make check ; ./loop.sh"
