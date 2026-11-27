# js-test-fixture-tool-reuse: facts for the owner's upstream PR

- **Branch:** DSpotDevelopers/pants `upstream-prep/js-test-fixture-tool-reuse` at `3bc73a73b`, on `pantsbuild/pants main 83e5bf9f0`. Our patch: new (JS test fixtures).
- **Files:** `src/python/pants/backend/javascript/goals/test_integration_test.py`.
- **Tests:** `src/python/pants/backend/javascript/goals/test_integration_test.py`. Run: `pants test src/python/pants/backend/javascript/goals/test_integration_test.py`.
- **Release note:** none (no user-facing change).
- **Disclosure (upstream requires it):** the code and tests were written by an LLM agent (Claude, Claude Code) and reviewed on our fork by our review lines; the owner reviews and tests it before opening.
- **Notes:** Tests only: no release note.

## Feedback applied
- F7
- F1: every added comment read (27 Nov 18:50Z); they say why

## What the owner's description needs
(Facts to write from: upstream requires a human-written title and description.)
- **Problem:** `javascript/goals/test_integration_test.py` builds a new engine for every case and so downloads its tools again for each.
- **Change:** One engine keeps the downloaded tools and their immutable inputs; each case still starts with an empty project and a new session.
- **Tests:** The same file's cases.

## Evidence
- In our Pants build (dspot-company-data runs it daily); not run on upstream main here (no Rust toolchain on this host).
