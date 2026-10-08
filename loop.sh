#!/usr/bin/env bash
# Outer loop: goal (SPEC.md) -> plan (PLAN.md) -> iterate with a fresh agent session each time.
# The agent edits code and may ADD subtasks. The HARNESS validates, verifies, ticks and commits.
#
# Phases: [plan] only when PLAN.md is missing (greenfield), then [loop].
# Env: MAX_ITER=12 MAX_FAILS=3 ITER_TIMEOUT=600 PLAN_TRIES=3 AUTO_APPROVE=0
#      AGENT_CMD='cursor-agent -p --force --output-format text'
set -uo pipefail
cd "$(dirname "$0")"
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"

MAX_ITER=${MAX_ITER:-12}
MAX_FAILS=${MAX_FAILS:-3}
ITER_TIMEOUT=${ITER_TIMEOUT:-600}
PLAN_TRIES=${PLAN_TRIES:-3}
AGENT_CMD=${AGENT_CMD:-cursor-agent -p --force --output-format text}
PROTECTED='tests/acceptance eval data SPEC.md harness loop.sh .cursor src/minisearch/evaluate.py'

git rev-parse --git-dir >/dev/null 2>&1 || { echo "not a git repo: git init -b main && git add -A && git commit -m baseline"; exit 3; }
[ -z "$(git status --porcelain)" ] || { echo "working tree is dirty: commit or stash first"; exit 3; }
[ -f SPEC.md ] || { echo "no SPEC.md: run ./use_mode.sh brownfield|greenfield first"; exit 3; }

BRANCH="loop/$(date +%m%d-%H%M%S)"
git checkout -q -b "$BRANCH"
mkdir -p .loop/runs
echo "branch: $BRANCH"

VIOL=0
revert_protected() {  # the harness, not the prompt, enforces the oracle
  VIOL=0
  for p in $PROTECTED; do
    if ! git diff --quiet HEAD -- "$p" 2>/dev/null || [ -n "$(git ls-files --others --exclude-standard -- "$p")" ]; then
      echo "🚫 protected path touched: $p (reverted)"; VIOL=$((VIOL+1))
      git checkout -q HEAD -- "$p" 2>/dev/null; git clean -fdq -- "$p" 2>/dev/null
    fi
  done
}

plan_phase() {
  rm -f .loop/plan_errors.txt
  for t in $(seq 1 "$PLAN_TRIES"); do
    echo; echo "=== PLAN phase, try $t/$PLAN_TRIES"
    prompt="$(cat .cursor/commands/plan.md)"
    if [ -s .loop/plan_errors.txt ]; then
      prompt="$prompt

THE HARNESS REJECTED YOUR PREVIOUS PLAN:
$(cat .loop/plan_errors.txt)
Fix every problem and rewrite PLAN.md."
    fi
    LOOP_PHASE=plan LOOP_PLAN_TRY=$t timeout "$ITER_TIMEOUT" $AGENT_CMD "$prompt" \
      2>&1 | tee ".loop/runs/plan-$t.log" | tail -n 8
    revert_protected
    if [ ! -f PLAN.md ]; then echo "- PLAN.md was not written" > .loop/plan_errors.txt; continue; fi
    if python3 harness/validate_plan.py > .loop/plan_errors.txt 2>&1; then rm -f .loop/plan_errors.txt; return 0; fi
    echo "❌ plan rejected by the harness:"; cat .loop/plan_errors.txt
    mv PLAN.md ".loop/runs/plan-$t.rejected.md"
  done
  return 1
}

approve_plan() {
  echo; echo "──────── proposed PLAN.md ────────"; cat PLAN.md; echo "──────────────────────────────────"
  if [ "${AUTO_APPROVE:-0}" = 1 ]; then echo "(AUTO_APPROVE=1)"; return 0; fi
  if [ ! -t 0 ]; then echo "plan needs human approval: run in a terminal or set AUTO_APPROVE=1"; return 1; fi
  read -r -p "Approve this plan? [y/N] " a; [ "$a" = y ] || [ "$a" = Y ]
}

if [ ! -f PLAN.md ]; then
  plan_phase || { echo "⛔ no valid plan after $PLAN_TRIES tries: human needed"; exit 3; }
  if ! approve_plan; then
    mv PLAN.md PLAN.proposed.md
    echo "plan not approved. Edit PLAN.proposed.md, rename to PLAN.md, commit, rerun."; exit 5
  fi
  git add -A && git commit -q -m "plan: validated and approved"
else
  python3 harness/validate_plan.py || { echo "⛔ plan lint failed (see above): human needed"; exit 3; }
fi

echo "iter,task,task_check,regression,plan_changed,violations,seconds" > .loop/metrics.csv
declare -A FAILS=()

for i in $(seq 1 "$MAX_ITER"); do
  nxt=$(python3 harness/plan.py next); rc=$?
  if [ $rc -eq 1 ]; then
    echo "✅ plan complete after $((i-1)) iterations ($(python3 harness/plan.py status))"; exit 0
  elif [ $rc -eq 4 ]; then echo "⛔ only blocked tasks left: human needed"; exit 2
  elif [ $rc -ne 0 ]; then echo "⛔ invalid plan (task without 'done when'): human needed"; exit 3
  fi
  id=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["id"])' "$nxt")
  title=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["title"])' "$nxt")
  check=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["check"])' "$nxt")
  echo; echo "=== iter $i/$MAX_ITER  $id: $title"; echo "    done when: $check"

  plan_before=$(sha1sum PLAN.md | cut -d' ' -f1)
  prompt="$(cat .cursor/commands/next-task.md)

ITERATION: $i
TASK: $id $title
DONE WHEN (harness runs this, exit code 0 = done): $check"

  start=$(date +%s)
  LOOP_PHASE=iter LOOP_ITER=$i LOOP_TASK_ID=$id LOOP_TASK_TITLE="$title" \
    timeout "$ITER_TIMEOUT" $AGENT_CMD "$prompt" 2>&1 | tee ".loop/runs/iter-$i.log" | tail -n 15
  secs=$(( $(date +%s) - start ))

  # 1. oracle protection and plan integrity: only subtasks may be added
  revert_protected; viol=$VIOL
  if [ "$(sha1sum PLAN.md | cut -d' ' -f1)" != "$plan_before" ]; then
    if ! python3 harness/validate_plan.py --diff-head > .loop/plan_diff_errors.txt 2>&1; then
      echo "🚫 illegal plan edit (reverted):"; cat .loop/plan_diff_errors.txt
      git checkout -q HEAD -- PLAN.md; viol=$((viol+1))
    fi
  fi

  # 2. objective verification, outside the agent
  bash -c "$check" >.loop/last_check.txt 2>&1; task_ok=$?
  make check >.loop/last_regress.txt 2>&1; reg_ok=$?
  replanned=0; [ "$(sha1sum PLAN.md | cut -d' ' -f1)" != "$plan_before" ] && replanned=1

  if [ $task_ok -eq 0 ] && [ $reg_ok -eq 0 ]; then
    python3 harness/plan.py done "$id"; rm -f .loop/last_failure.txt
    FAILS[$id]=0; status="DONE"
  else
    status="FAIL"
    { echo "iteration $i, task $id: task_check_exit=$task_ok regression_exit=$reg_ok"
      echo "--- task check output (tail):"; tail -n 25 .loop/last_check.txt
      echo "--- make check output (tail):"; tail -n 15 .loop/last_regress.txt
    } > .loop/last_failure.txt
    # a legal replan is progress, not a repeat failure of the same task
    if [ $replanned -eq 1 ]; then FAILS[$id]=0; else FAILS[$id]=$(( ${FAILS[$id]:-0} + 1 )); fi
  fi

  echo "$i,$id,$task_ok,$reg_ok,$replanned,$viol,$secs" >> .loop/metrics.csv
  echo "    -> $status  (task_check=$task_ok regression=$reg_ok replanned=$replanned violations=$viol, ${secs}s)"
  git add -A && git commit -q -m "iter $i: $id $status$([ $replanned -eq 1 ] && echo ' [replanned]')" || true

  if [ "${FAILS[$id]:-0}" -ge "$MAX_FAILS" ]; then
    python3 harness/plan.py block "$id"; git commit -qam "iter $i: $id BLOCKED after $MAX_FAILS failures"
    echo "⛔ $id failed $MAX_FAILS times without replanning: escalating to a human"; exit 2
  fi
done
echo "🛑 iteration budget ($MAX_ITER) exhausted; $(python3 harness/plan.py status)"; exit 1
