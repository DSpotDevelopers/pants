# faas-test-ambient-store: facts for the owner's upstream PR

- **Branch:** DSpotDevelopers/pants `upstream-prep/faas-test-ambient-store` at `3d88d9f29`, on `pantsbuild/pants main 83e5bf9f0`. Our patch: new (FaaS test fixture).
- **Files:** `src/python/pants/backend/python/util_rules/faas_test.py`.
- **Tests:** `src/python/pants/backend/python/util_rules/faas_test.py`. Run: `pants test src/python/pants/backend/python/util_rules/faas_test.py`.
- **Release note:** none (no user-facing change).
- **Disclosure (upstream requires it):** the code and tests were written by an LLM agent (Claude, Claude Code) and reviewed on our fork by our review lines; the owner reviews and tests it before opening.
- **Notes:** Tests only: no release note.

## Feedback applied
- F7
- resolved beside upstream's new `create_subsystem` import
- F1: every added comment read (27 Nov 18:50Z); they say why

## What the owner's description needs
(Facts to write from: upstream requires a human-written title and description.)
- **Problem:** `faas_test.py`'s rule runner opens the ambient local store, so an unrelated, unavailable cache fails source/digest tests that need no store.
- **Change:** The fixture uses its own local store options.
- **Tests:** A case run with the ambient store unavailable.

## Evidence
- In our Pants build (dspot-company-data runs it daily); not run on upstream main here (no Rust toolchain on this host).
