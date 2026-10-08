# Agent harness demo: minisearch, two modes

A tiny search library (hashing embedder + cosine, English and Russian, stdlib only) used as a target
for an **agentic harness**: goal -> plan -> loop, with objective checks outside the agent.

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
```bash
python -m venv .venv && source .venv/bin/activate && pip install pytest ruff
./use_mode.sh greenfield            # or brownfield
git init -b main && git add -A && git commit -m baseline
AGENT_CMD='python3 demo/fake_agent.py' AUTO_APPROVE=1 ./loop.sh   # rehearsal, no API, ~5 s
./loop.sh                                                         # real: cursor-agent
```
Real run: use a **separate copy** with `./use_mode.sh <mode> --strip` (removes `modes/`, `demo/`, `DEMO.md`)
so the agent cannot read the reference solution. `.cursorignore` also hides them (best effort).

Env: `MAX_ITER=12 MAX_FAILS=3 ITER_TIMEOUT=600 PLAN_TRIES=3 AUTO_APPROVE=0 AGENT_CMD=...`

## What the harness enforces (not the prompt)
- Plan phase: plan must have a `done when` per task, cover every acceptance test, and every check must be red now.
- Human approval of the plan before the loop (or `AUTO_APPROVE=1`).
- Per iteration: fresh agent session; edits to the oracle are reverted; plan edits other than *adding subtasks*
  are reverted; the harness runs the task check and `make check` itself, ticks the box, commits to `loop/*`.
- Stop conditions: iteration budget, per-iteration timeout, repeated failure without replanning -> `[!]` + escalation.
- `.loop/metrics.csv`: per iteration task, check results, replanned, violations, seconds.
