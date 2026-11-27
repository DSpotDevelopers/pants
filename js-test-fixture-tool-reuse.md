# js-test-fixture-tool-reuse: facts for the owner's upstream PR

- **Branch:** DSpotDevelopers/pants `upstream-prep/js-test-fixture-tool-reuse` at `3bc73a73b`, on `pantsbuild/pants main 83e5bf9f0`. Our patch: new (JS test fixtures).
- **Files:** `src/python/pants/backend/javascript/goals/test_integration_test.py`.
- **Tests:** `src/python/pants/backend/javascript/goals/test_integration_test.py`. Run: `pants test src/python/pants/backend/javascript/goals/test_integration_test.py`.
- **Release note:** none (no user-facing change).
- **Disclosure (upstream requires it):** the code and tests were written by an LLM agent (Claude, Claude Code) and reviewed on our fork by our review lines; the owner reviews and tests it before opening.
- **Notes:** Tests only: no release note.

## Feedback applied
- F7
- F1: not yet read line by line for comment style; the owner's review, or ours before he opens it

## What the owner's description needs: the facts, from the branch's own commits
(Upstream requires a human-written title and description: these are facts to write from, not text to paste. Some commit
bodies mention our fork's context; the squash commit takes the owner's description instead.)

### test(javascript): expose repeated engine setup between fixture cases


### test(javascript): reuse tools while resetting each fixture project

## Evidence
- In our Pants build (dspot-company-data runs it daily); not run on upstream main here (no Rust toolchain on this host).
