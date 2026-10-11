# Agent harness demo: minisearch, two modes

A tiny search library (hashing embedder + cosine, English and Russian, stdlib only) used as a target
for an **agentic harness**: goal -> plan -> loop, with objective checks outside the agent.
The completed result supports backward-compatible text output plus UTF-8 JSON/CSV export.

Документация:
- [полный комплект Markdown-документации на русском](docs/ru/README.md);
- [поисковик для заказчика](ДЛЯ_ЗАКАЗЧИКА.md);
- [Harness для заказчика](HARNESS_ДЛЯ_ЗАКАЗЧИКА.md);
- [исходный проект и выполненные доработки](ИСХОДНЫЙ_ПРОЕКТ_И_ДОРАБОТКИ.md);
- [пример тестовых данных](examples/test-data/README.md);
- [готовый пример JSON/CSV-выгрузки](examples/test-output/README.md).

| Mode | Start state | Who writes the plan | Shows |
|---|---|---|---|
| `brownfield` | working code, 3 missing features | human (`PLAN.md` ships) | loop, dynamic replanning, protections |
| `greenfield` | contract in `SPEC.md`, empty `src/` | **the agent** (`/plan`), validated by the harness, approved by a human | everything above + goal -> plan |

## Layout
```
harness/plan.py, validate_plan.py   plan parser; plan validator (shape, oracle coverage, red-at-start, subtasks-only)
loop.sh                             [plan phase] + loop, shared by both modes
.cursor/                            rules, commands (/plan /next-task /replan), hooks, .cursorignore at root
tests/acceptance/, eval/, data/     the ORACLE: human-written, protected from the agent
modes/<mode>/                       overlay copied into the tree by use_mode.sh
demo/                               fake_agent.py (offline rehearsal), reference_solution.patch, reset.sh
```

## Quick start

Windows PowerShell:
```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
.\use_mode.ps1 greenfield           # or brownfield
git add -A; git commit -m "greenfield baseline"
$env:AUTO_APPROVE = "1"
.\loop.ps1                           # real: Cursor Agent CLI
```

Linux/macOS:
```bash
python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
./use_mode.sh greenfield            # or brownfield
git add -A && git commit -m "greenfield baseline"
AUTO_APPROVE=1 ./loop.sh
```

Real run: use a **separate copy** with `use_mode.ps1 <mode> --strip` or
`./use_mode.sh <mode> --strip` (removes `modes/`, `demo/`, `DEMO.md`)
so the agent cannot read the reference solution. `.cursorignore` also hides them (best effort).

Env: `MAX_ITER=12 MAX_FAILS=3 ITER_TIMEOUT=600 PLAN_TRIES=3 AUTO_APPROVE=0 AGENT_CMD=...`

## What the harness enforces (not the prompt)
- Plan phase: plan must have a `done when` per task, cover every acceptance test, and every check must be red now.
- Human approval of the plan before the loop (or `AUTO_APPROVE=1`).
- Per iteration: fresh agent session; edits to the oracle are reverted; plan edits other than *adding subtasks*
  are reverted; the harness runs the task check and `make check` itself, ticks the box, commits to `loop/*`.
- Stop conditions: iteration budget, per-iteration timeout, repeated failure without replanning -> `[!]` + escalation.
- `.loop/metrics.csv`: per iteration task, check results, replanned, violations, seconds.
