# PLAN

Build `minisearch` greenfield per SPEC.md. Features in delivery order; each task is one iteration.

- [x] T1 Core library, CLI search, English recall
  - done when: `pytest -q tests/acceptance/test_core.py && python -m minisearch.evaluate --set en --min-recall 0.8`
- [x] T2 Index persistence and CLI index/search roundtrip
  - done when: `pytest -q tests/acceptance/test_persistence.py`
- [x] T3 Russian tokenization and recall without English regression
  - done when: `pytest -q tests/acceptance/test_russian.py && python -m minisearch.evaluate --set ru --min-recall 0.9`
- [x] T4 Language filter on search API and CLI
  - done when: `pytest -q tests/acceptance/test_lang_filter.py`
