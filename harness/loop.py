"""Cross-platform two-phase agentic development loop.

Greenfield mode starts with a planning phase. Brownfield mode starts from a
human-written PLAN.md. In both modes the harness owns validation, protected
paths, objective checks, commits, metrics, and stop conditions.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import time
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOOP_DIR = ROOT / ".loop"
RUNS_DIR = LOOP_DIR / "runs"
PROTECTED = (
    "tests/acceptance",
    "eval",
    "data",
    "SPEC.md",
    "harness",
    "loop.sh",
    "loop.ps1",
    "use_mode.sh",
    "use_mode.ps1",
    "reset.sh",
    "reset.ps1",
    ".cursor",
    "src/minisearch/evaluate.py",
)
REGRESSION_CHECKS = (
    ("lint", (sys.executable, "-m", "ruff", "check", ".")),
    ("tests", (sys.executable, "-m", "pytest", "-q")),
    (
        "eval-en",
        (sys.executable, "-m", "minisearch.evaluate", "--set", "en", "--min-recall", "0.8"),
    ),
)


def run(
    args: list[str] | tuple[str, ...],
    *,
    capture: bool = True,
    check: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        capture_output=capture,
        text=True,
        check=check,
        env=env,
    )


def git(*args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    return run(("git", *args), check=check)


def plan(command: str, task_id: str | None = None) -> subprocess.CompletedProcess[str]:
    args = [sys.executable, "-m", "harness.plan", command]
    if task_id:
        args.append(task_id)
    return run(args)


def validate_plan(*, diff_head: bool = False) -> subprocess.CompletedProcess[str]:
    args = [sys.executable, "-m", "harness.validate_plan"]
    if diff_head:
        args.append("--diff-head")
    return run(args)


def plan_hash() -> str:
    return hashlib.sha1((ROOT / "PLAN.md").read_bytes()).hexdigest()


def parse_agent_command(value: str) -> list[str]:
    args = shlex.split(value, posix=os.name != "nt")
    if not args:
        raise ValueError("AGENT_CMD is empty")
    if os.name == "nt" and args[0] in {"agent", "cursor-agent"}:
        executable = shutil.which(args[0])
        if not executable and os.environ.get("LOCALAPPDATA"):
            candidate = Path(os.environ["LOCALAPPDATA"]) / "cursor-agent" / f"{args[0]}.cmd"
            if candidate.exists():
                executable = str(candidate)
        if executable:
            args[0] = executable
    return args


def parse_check(command: str) -> list[list[str]]:
    """Parse a PLAN check into allowlisted argv lists, never a shell command."""
    if any(token in command for token in (";", "|", ">", "<", "`", "\n", "\r", "$(")):
        raise ValueError("shell operators are not allowed in done-when checks")
    chunks = [chunk.strip() for chunk in command.split("&&")]
    if not chunks or any(not chunk for chunk in chunks):
        raise ValueError("empty command in done-when check")

    parsed: list[list[str]] = []
    for chunk in chunks:
        args = shlex.split(chunk, posix=True)
        if not args:
            raise ValueError("empty done-when command")
        if args[0] == "pytest":
            args = [sys.executable, "-m", "pytest", *args[1:]]
        elif args[0] in {"python", "python3"} and args[1:3] == [
            "-m",
            "minisearch.evaluate",
        ]:
            args[0] = sys.executable
        else:
            raise ValueError("done-when allows only pytest or python -m minisearch.evaluate")
        parsed.append(args)
    return parsed


def run_check_commands(commands: list[list[str]], output_path: Path) -> int:
    sections: list[str] = []
    result_code = 0
    for args in commands:
        result = run(args)
        sections.append(f"$ {shlex.join(args)}\n{result.stdout}{result.stderr}")
        if result.returncode:
            result_code = result.returncode
            break
    output_path.write_text("\n".join(sections), encoding="utf-8")
    return result_code


def run_regression(output_path: Path) -> int:
    sections: list[str] = []
    result_code = 0
    for name, args in REGRESSION_CHECKS:
        result = run(args)
        sections.append(f"## {name}\n$ {shlex.join(args)}\n{result.stdout}{result.stderr}")
        if result.returncode and result_code == 0:
            result_code = result.returncode
    output_path.write_text("\n".join(sections), encoding="utf-8")
    return result_code


def agent_environment(**extra: str) -> dict[str, str]:
    python_bin = str(Path(sys.executable).parent)
    return {
        **os.environ,
        "PATH": python_bin + os.pathsep + os.environ.get("PATH", ""),
        "PYTHONPATH": str(ROOT / "src")
        + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else ""),
        **extra,
    }


def run_agent(args: list[str], prompt: str, env: dict[str, str], timeout: int, log: Path) -> int:
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    process = subprocess.Popen(
        [*args, prompt],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        creationflags=creationflags,
        start_new_session=os.name != "nt",
    )
    try:
        output, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                check=False,
            )
        else:
            os.killpg(process.pid, signal.SIGTERM)
        output, _ = process.communicate()
        output += f"\nAgent timed out after {timeout}s\n"
    log.write_text(output, encoding="utf-8")
    for line in deque(output.splitlines(), maxlen=15):
        print(line)
    return process.returncode or 0


def changed(path: str) -> bool:
    return bool(git("status", "--porcelain", "--", path).stdout.strip())


def restore_protected() -> int:
    violations = 0
    for path in PROTECTED:
        if not changed(path):
            continue
        print(f"PROTECTED path touched: {path} (reverted)")
        violations += 1
        git("checkout", "-q", "HEAD", "--", path)
        git("clean", "-fdq", "--", path)
    return violations


def tail(path: Path, count: int) -> str:
    if not path.exists():
        return ""
    return "\n".join(deque(path.read_text(encoding="utf-8").splitlines(), maxlen=count))


def commit(message: str) -> None:
    git("add", "-A", check=True)
    result = git("commit", "-q", "-m", message)
    if result.returncode and "nothing to commit" not in f"{result.stdout}{result.stderr}":
        raise RuntimeError(result.stderr.strip() or "git commit failed")


def ensure_repository_ready() -> None:
    if git("rev-parse", "--git-dir").returncode:
        raise RuntimeError("not a git repo: initialize it and create a baseline commit")
    if git("status", "--porcelain").stdout.strip():
        raise RuntimeError("working tree is dirty: commit or stash first")
    if not (ROOT / "SPEC.md").exists():
        raise RuntimeError("no SPEC.md: run use_mode.ps1 brownfield|greenfield first")


def plan_phase(agent_command: list[str], timeout: int, tries: int) -> bool:
    errors_path = LOOP_DIR / "plan_errors.txt"
    errors_path.unlink(missing_ok=True)
    command_text = (ROOT / ".cursor/commands/plan.md").read_text(encoding="utf-8")

    for attempt in range(1, tries + 1):
        print(f"\n=== PLAN phase, try {attempt}/{tries}")
        prompt = command_text
        if errors_path.exists() and errors_path.stat().st_size:
            prompt += (
                "\n\nTHE HARNESS REJECTED YOUR PREVIOUS PLAN:\n"
                f"{errors_path.read_text(encoding='utf-8')}\n"
                "Fix every problem and rewrite PLAN.md."
            )
        run_agent(
            agent_command,
            prompt,
            agent_environment(LOOP_PHASE="plan", LOOP_PLAN_TRY=str(attempt)),
            timeout,
            RUNS_DIR / f"plan-{attempt}.log",
        )
        restore_protected()
        plan_path = ROOT / "PLAN.md"
        if not plan_path.exists():
            errors_path.write_text("- PLAN.md was not written\n", encoding="utf-8")
            continue
        validation = validate_plan()
        errors_path.write_text(
            f"{validation.stdout}{validation.stderr}",
            encoding="utf-8",
        )
        if validation.returncode == 0:
            errors_path.unlink(missing_ok=True)
            return True
        print("plan rejected by the harness:")
        print(errors_path.read_text(encoding="utf-8"))
        plan_path.replace(RUNS_DIR / f"plan-{attempt}.rejected.md")
    return False


def approve_plan(auto_approve: bool) -> bool:
    text = (ROOT / "PLAN.md").read_text(encoding="utf-8")
    print("\n-------- proposed PLAN.md --------")
    print(text)
    print("----------------------------------")
    if auto_approve:
        print("(AUTO_APPROVE=1)")
        return True
    if not sys.stdin.isatty():
        print("plan needs human approval: run in a terminal or set AUTO_APPROVE=1")
        return False
    return input("Approve this plan? [y/N] ").strip().lower() == "y"


def main() -> int:
    max_iter = int(os.environ.get("MAX_ITER", "12"))
    max_fails = int(os.environ.get("MAX_FAILS", "3"))
    iteration_timeout = int(os.environ.get("ITER_TIMEOUT", "600"))
    plan_tries = int(os.environ.get("PLAN_TRIES", "3"))
    auto_approve = os.environ.get("AUTO_APPROVE", "0") == "1"
    agent_command = parse_agent_command(
        os.environ.get("AGENT_CMD", "agent -p --force --output-format text --trust")
    )

    try:
        ensure_repository_ready()
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 3

    branch = time.strftime("loop/%m%d-%H%M%S")
    if git("checkout", "-q", "-b", branch).returncode:
        print(f"could not create branch {branch}", file=sys.stderr)
        return 3
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"branch: {branch}")

    if not (ROOT / "PLAN.md").exists():
        if not plan_phase(agent_command, iteration_timeout, plan_tries):
            print(f"no valid plan after {plan_tries} tries: human needed")
            return 3
        if not approve_plan(auto_approve):
            (ROOT / "PLAN.md").replace(ROOT / "PLAN.proposed.md")
            print("plan not approved; edit PLAN.proposed.md, rename to PLAN.md, commit, rerun")
            return 5
        commit("plan: validated and approved")
    else:
        validation = validate_plan()
        if validation.returncode:
            print(f"plan lint failed:\n{validation.stdout}{validation.stderr}")
            return 3

    metrics_path = LOOP_DIR / "metrics.csv"
    with metrics_path.open("w", newline="", encoding="utf-8") as metrics_file:
        csv.writer(metrics_file).writerow(
            ["iter", "task", "task_check", "regression", "plan_changed", "violations", "seconds"]
        )

    failures: dict[str, int] = {}
    for iteration in range(1, max_iter + 1):
        next_task = plan("next")
        if next_task.returncode == 1:
            status = plan("status").stdout.strip()
            print(f"plan complete after {iteration - 1} iterations ({status})")
            return 0
        if next_task.returncode == 4:
            print("only blocked tasks left: human needed")
            return 2
        if next_task.returncode != 0:
            print("invalid plan: human needed")
            return 3

        task = json.loads(next_task.stdout)
        task_id, title, check_text = task["id"], task["title"], task["check"]
        try:
            check_commands = parse_check(check_text)
        except ValueError as exc:
            print(f"invalid done when for {task_id}: {exc}")
            return 3

        print(f"\n=== iter {iteration}/{max_iter}  {task_id}: {title}")
        print(f"    done when: {check_text}")
        before = plan_hash()
        command_text = (ROOT / ".cursor/commands/next-task.md").read_text(encoding="utf-8")
        prompt = (
            f"{command_text}\n\nITERATION: {iteration}\nTASK: {task_id} {title}\n"
            f"DONE WHEN (harness runs this, exit code 0 = done): {check_text}"
        )

        started = time.monotonic()
        run_agent(
            agent_command,
            prompt,
            agent_environment(
                LOOP_PHASE="iter",
                LOOP_ITER=str(iteration),
                LOOP_TASK_ID=task_id,
                LOOP_TASK_TITLE=title,
            ),
            iteration_timeout,
            RUNS_DIR / f"iter-{iteration}.log",
        )
        seconds = int(time.monotonic() - started)

        violations = restore_protected()
        if plan_hash() != before:
            validation = validate_plan(diff_head=True)
            if validation.returncode:
                print(f"illegal plan edit (reverted):\n{validation.stdout}{validation.stderr}")
                git("checkout", "-q", "HEAD", "--", "PLAN.md")
                violations += 1

        task_ok = run_check_commands(check_commands, LOOP_DIR / "last_check.txt")
        regression_ok = run_regression(LOOP_DIR / "last_regress.txt")
        replanned = plan_hash() != before
        failure_path = LOOP_DIR / "last_failure.txt"

        if task_ok == 0 and regression_ok == 0:
            plan("done", task_id)
            failure_path.unlink(missing_ok=True)
            failures[task_id] = 0
            status = "DONE"
        else:
            status = "FAIL"
            failure_path.write_text(
                f"iteration {iteration}, task {task_id}: "
                f"task_check_exit={task_ok} regression_exit={regression_ok}\n"
                f"--- task check output (tail):\n{tail(LOOP_DIR / 'last_check.txt', 25)}\n"
                f"--- regression output (tail):\n{tail(LOOP_DIR / 'last_regress.txt', 15)}\n",
                encoding="utf-8",
            )
            failures[task_id] = 0 if replanned else failures.get(task_id, 0) + 1

        with metrics_path.open("a", newline="", encoding="utf-8") as metrics_file:
            csv.writer(metrics_file).writerow(
                [
                    iteration,
                    task_id,
                    task_ok,
                    regression_ok,
                    int(replanned),
                    violations,
                    seconds,
                ]
            )
        print(
            f"    -> {status} (task_check={task_ok} regression={regression_ok} "
            f"replanned={int(replanned)} violations={violations}, {seconds}s)"
        )
        message = f"iter {iteration}: {task_id} {status}"
        if replanned:
            message += " [replanned]"
        commit(message)

        if failures.get(task_id, 0) >= max_fails:
            plan("block", task_id)
            commit(f"iter {iteration}: {task_id} BLOCKED")
            print(f"{task_id} failed {max_fails} times without replanning: human needed")
            return 2

    print(f"iteration budget ({max_iter}) exhausted; {plan('status').stdout.strip()}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
