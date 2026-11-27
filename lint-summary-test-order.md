# lint-summary-test-order: facts for the owner's upstream PR

- **Branch:** DSpotDevelopers/pants `upstream-prep/lint-summary-test-order` at `279cdb705`, on `pantsbuild/pants main 83e5bf9f0`. Our patch: fork #48.
- **Files:** `src/python/pants/core/goals/lint_test.py`.
- **Tests:** `src/python/pants/core/goals/lint_test.py`. Run: `pants test src/python/pants/core/goals/lint_test.py`.
- **Release note:** none (no user-facing change).
- **Disclosure (upstream requires it):** the code and tests were written by an LLM agent (Claude, Claude Code) and reviewed on our fork by our review lines; the owner reviews and tests it before opening.
- **Notes:** Test only: a fixture that relied on set order. No release note.

## Feedback applied
- F7
- F1: every added comment read (27 Nov 18:50Z); they say why

## What the owner's description needs
(Facts to write from: upstream requires a human-written title and description.)
- **Problem:** A `lint` goal test fixture relied on set iteration order for its summary requests.
- **Change:** The fixture keeps the configured request order.
- **Tests:** The `lint_test.py` case that exposed it.

## Evidence
- In our Pants build (dspot-company-data runs it daily); not run on upstream main here (no Rust toolchain on this host).
