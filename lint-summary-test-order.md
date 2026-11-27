# lint-summary-test-order: facts for the owner's upstream PR

- **Branch:** DSpotDevelopers/pants `upstream-prep/lint-summary-test-order` at `279cdb705`, on `pantsbuild/pants main 83e5bf9f0`. Our patch: fork #48.
- **Files:** `src/python/pants/core/goals/lint_test.py`.
- **Tests:** `src/python/pants/core/goals/lint_test.py`. Run: `pants test src/python/pants/core/goals/lint_test.py`.
- **Release note:** none (no user-facing change).
- **Disclosure (upstream requires it):** the code and tests were written by an LLM agent (Claude, Claude Code) and reviewed on our fork by our review lines; the owner reviews and tests it before opening.
- **Notes:** Test only: a fixture that relied on set order. No release note.

## Feedback applied
- F7
- F1: not yet read line by line for comment style; the owner's review, or ours before he opens it

## What the owner's description needs: the facts, from the branch's own commits
(Upstream requires a human-written title and description: these are facts to write from, not text to paste. Some commit
bodies mention our fork's context; the squash commit takes the owner's description instead.)

### test(lint): expose unordered summary request fixture


### fix(lint): preserve request order in summary test fixture

## Evidence
- In our Pants build (dspot-company-data runs it daily); not run on upstream main here (no Rust toolchain on this host).
