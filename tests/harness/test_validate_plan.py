from harness.plan import parse
from harness.validate_plan import coverage_errors, diff_errors, shape_errors

OLD = """\
- [ ] T1 core
  - done when: `pytest -q tests/acceptance/test_core.py`
- [ ] T2 russian
  - done when: `pytest -q tests/acceptance/test_russian.py`
"""


def test_valid_plan_has_no_shape_errors():
    assert shape_errors(parse(OLD)) == []


def test_missing_check_and_duplicate_ids_are_reported():
    bad = "- [ ] T1 a\n- [ ] T1 b\n  - done when: `true`\n"
    errs = shape_errors(parse(bad))
    assert any("duplicate" in e for e in errs) and any("missing" in e for e in errs)


def test_coverage_requires_every_acceptance_file():
    errs = coverage_errors(parse(OLD), ["test_core.py", "test_lang_filter.py"])
    assert errs == ["acceptance test test_lang_filter.py is not the `done when` of any task"]


def test_adding_a_subtask_is_allowed():
    new = OLD + "  - [ ] T2.1 stem\n    - done when: `pytest -q tests/unit`\n"
    assert diff_errors(parse(OLD), parse(new)) == []


def test_changing_removing_or_ticking_existing_tasks_is_rejected():
    changed = OLD.replace("`pytest -q tests/acceptance/test_core.py`", "`true`")
    assert any("changed" in e for e in diff_errors(parse(OLD), parse(changed)))
    ticked = OLD.replace("- [ ] T1", "- [x] T1")
    assert any("changed" in e for e in diff_errors(parse(OLD), parse(ticked)))
    removed = "\n".join(OLD.splitlines()[:2]) + "\n"
    assert any("removed" in e for e in diff_errors(parse(OLD), parse(removed)))


def test_new_top_level_task_or_orphan_subtask_is_rejected():
    top = OLD + "- [ ] T9 extra\n  - done when: `true`\n"
    assert any("top-level" in e for e in diff_errors(parse(OLD), parse(top)))
    orphan = OLD + "  - [ ] T7.1 x\n    - done when: `true`\n"
    assert any("parent" in e for e in diff_errors(parse(OLD), parse(orphan)))
