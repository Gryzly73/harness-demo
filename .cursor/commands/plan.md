You are the PLANNING phase of an autonomous development loop. Write code NOWHERE in this phase.

Read `SPEC.md` and look at `tests/acceptance/` and `eval/`. Then write `PLAN.md`:

- Format, one task per block, ids `T1`, `T2`, ... in delivery order:
  `- [ ] T<n> <title>` and directly below it `  - done when: \`<shell command>\``.
- Every task is small enough for ONE iteration (one fresh agent session, one commit).
- `done when` must be a command that is RED today and goes green only when the task is truly done.
  Prefer the existing acceptance tests and `python -m minisearch.evaluate ...`; never use `true`.
- EVERY file in `tests/acceptance/` must be the `done when` (or part of it) of some task.
- Order tasks so that earlier ones unblock later ones (the core library comes first).
- Leave all checkboxes unchecked. Do not touch any file except `PLAN.md`.

The harness validates the plan (shape, coverage, red-at-start) and a human approves it before the loop starts.
