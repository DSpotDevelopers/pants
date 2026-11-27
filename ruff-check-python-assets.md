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
- F1: not yet read line by line for comment style; the owner's review, or ours before he opens it

## What the owner's description needs: the facts, from the branch's own commits
(Upstream requires a human-written title and description: these are facts to write from, not text to paste. Some commit
bodies mention our fork's context; the squash commit takes the owner's description instead.)

### test(ruff): `ruff check` lints the Python files of file and resource targets when asked

Adds `[ruff].check_python_assets` (default off; declared only, no behaviour yet) and six
goal-level cells through `pants lint --only=ruff-check`:
- with the option, a bad `.py` in a `resources` or a `files` target fails the lint;
- a `.txt` resource beside them is never given to Ruff;
- without the option, nothing is linted;
- `skip_ruff_check=True` and `skip_ruff=True` opt a `file`/`resource` target out.

Red on this commit: 5 of the 6 fail. The enabled cells get exit 0 and Ruff never runs
(stock Ruff lints only Python targets), and both skip fields are refused on `resources`.
The default-off cell passes.


### ruff: optionally lint the Python files of file and resource targets

`[ruff].check_python_assets` (default off) adds a second lint request
under the same `ruff-check` id for the `.py` files of `file` and
`resource` targets, so `--only=ruff-check` runs both, with the same Ruff,
config and report. `skip_ruff_check` and `skip_ruff` are accepted on
those targets.

## Evidence
- In our Pants build (dspot-company-data runs it daily); not run on upstream main here (no Rust toolchain on this host).
