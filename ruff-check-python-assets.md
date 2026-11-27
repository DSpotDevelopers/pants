# ruff-check-python-assets: facts for the owner's upstream PR

- **Branch:** DSpotDevelopers/pants `upstream-prep/ruff-check-python-assets` at `d483333f0`, on `pantsbuild/pants main 83e5bf9f0`. Our patch: 14.
- **Files:** `docs/notes/2.35.x.md`, `src/python/pants/backend/python/lint/ruff/check/rules.py`, `src/python/pants/backend/python/lint/ruff/check/skip_field.py`, `src/python/pants/backend/python/lint/ruff/rules_integration_test.py`, `src/python/pants/backend/python/lint/ruff/skip_field.py`, `src/python/pants/backend/python/lint/ruff/subsystem.py`.
- **Tests:** `src/python/pants/backend/python/lint/ruff/rules_integration_test.py`. Run: `pants test src/python/pants/backend/python/lint/ruff/rules_integration_test.py`.
- **Release note:** in the branch, `docs/notes/2.35.x.md`, "#### Python".
- **Disclosure (upstream requires it):** the code and tests were written by an LLM agent (Claude, Claude Code) and reviewed on our fork by our review lines; the owner reviews and tests it before opening.
- **Notes:** A new option (default off); upstream may ask for docs in docs/docs/python/overview/linters-and-formatters.mdx.

## Feedback applied
- F4: note names the new option and its default
- F7
- F1: every added comment read (27 Nov 18:50Z); they say why

## What the owner's description needs
(Facts to write from: upstream requires a human-written title and description.)
- **Problem:** `ruff check` lints only `python_source(s)`/`python_test(s)` targets, so the `.py` files a repository owns as `file`/`resource` (test fixtures, Python read as data) are never linted by Pants.
- **Change:** New `[ruff].check_python_assets` (default off): a second lint request under the same `ruff-check` id for those files, with the same Ruff, config and report; `skip_ruff_check`/`skip_ruff` work on `file`/`resource` targets. A non-`.py` resource beside them is never given to Ruff.
- **Tests:** Six cases in `ruff/rules_integration_test.py` (on, off, skip fields, `--only=ruff-check`, non-Python resources).

## Evidence
- In our Pants build (dspot-company-data runs it daily); not run on upstream main here (no Rust toolchain on this host).
