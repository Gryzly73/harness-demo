"""Plan validation: the harness does not trust a plan just because an agent wrote it.

  python harness/validate_plan.py              initial plan: shape, coverage of the oracle,
                                               every unchecked task is RED right now
  python harness/validate_plan.py --diff-head  agent edits during the loop: only subtasks
                                               may be added, nothing existing may change
Exit 0 = valid, 1 = invalid (reasons on stdout).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

try:  # works both as `python harness/validate_plan.py` and as an imported module
    from harness.loop import parse_check
    from harness.plan import PLAN, Task, parse
except ImportError:  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from harness.loop import parse_check
    from harness.plan import PLAN, Task, parse

ROOT = Path(__file__).resolve().parents[1]
CHECK_TIMEOUT = 120


def shape_errors(tasks: list[Task], *, allow_completed: bool = False) -> list[str]:
    errors: list[str] = []
    if not tasks:
        return ["plan has no tasks (expected lines like `- [ ] T1 title`)"]
    seen: set[str] = set()
    for t in tasks:
        if t.id in seen:
            errors.append(f"duplicate task id {t.id}")
        seen.add(t.id)
        if not t.check:
            errors.append(f"{t.id}: missing line `  - done when: \\`<command>\\``")
        if t.mark != " " and not (allow_completed and t.mark == "x"):
            errors.append(f"{t.id}: new plans must start unchecked, found [{t.mark}]")
    return errors


def coverage_errors(tasks: list[Task], acceptance: list[str]) -> list[str]:
    checks = " ".join(t.check or "" for t in tasks)
    return [
        f"acceptance test {name} is not the `done when` of any task"
        for name in acceptance
        if name not in checks
    ]


def red_errors(tasks: list[Task], *, allow_completed: bool = False) -> list[str]:
    errors: list[str] = []
    for t in tasks:
        if t.mark not in ({" ", "x"} if allow_completed else {" "}) or not t.check:
            continue
        try:
            commands = parse_check(t.check)
        except ValueError as exc:
            errors.append(f"{t.id}: unsafe or unsupported `done when`: {exc}")
            continue
        try:
            rc = 0
            for command in commands:
                rc = subprocess.run(
                    command, cwd=ROOT, capture_output=True, timeout=CHECK_TIMEOUT
                ).returncode
                if rc:
                    break
        except subprocess.TimeoutExpired:
            errors.append(f"{t.id}: `done when` timed out after {CHECK_TIMEOUT}s")
            continue
        if t.mark == " " and rc == 0:
            errors.append(f"{t.id}: `done when` already passes: vacuous check or task already done")
        elif t.mark == "x" and rc != 0:
            errors.append(f"{t.id}: marked complete but `done when` fails")
    return errors


def diff_errors(old: list[Task], new: list[Task]) -> list[str]:
    errors: list[str] = []
    new_by_id = {t.id: t for t in new}
    old_ids = {t.id for t in old}
    for o in old:
        n = new_by_id.get(o.id)
        if n is None:
            errors.append(f"{o.id}: existing task was removed")
        elif (n.title, n.check, n.mark) != (o.title, o.check, o.mark):
            errors.append(f"{o.id}: existing task was changed (title, check or checkbox)")
    for n in new:
        if n.id in old_ids:
            continue
        if "." not in n.id:
            errors.append(f"{n.id}: new top-level task; only subtasks (e.g. T1.1) may be added")
        elif n.id.rsplit(".", 1)[0] not in new_by_id:
            errors.append(f"{n.id}: parent {n.id.rsplit('.', 1)[0]} does not exist")
        if not n.check:
            errors.append(f"{n.id}: subtask has no `done when` command")
        if n.mark != " ":
            errors.append(f"{n.id}: subtask must start unchecked")
    return errors


def _acceptance_files() -> list[str]:
    d = ROOT / "tests" / "acceptance"
    return sorted(p.name for p in d.glob("test_*.py")) if d.is_dir() else []


def main(argv: list[str]) -> int:
    if not PLAN.exists():
        print("- PLAN.md does not exist")
        return 1
    new = parse(PLAN.read_text(encoding="utf-8"))
    if "--diff-head" in argv:
        show = subprocess.run(
            ["git", "show", "HEAD:PLAN.md"], cwd=ROOT, capture_output=True, text=True
        )
        if show.returncode != 0:
            return 0  # no committed plan to compare with
        errors = diff_errors(parse(show.stdout), new)
    else:
        allow_completed = "--allow-completed" in argv
        errors = shape_errors(new, allow_completed=allow_completed)
        if not errors:
            errors += coverage_errors(new, _acceptance_files())
            errors += red_errors(new, allow_completed=allow_completed)
    for e in errors:
        print(f"- {e}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
