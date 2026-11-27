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
- F1: not yet read line by line for comment style; the owner's review, or ours before he opens it

## What the owner's description needs: the facts, from the branch's own commits
(Upstream requires a human-written title and description: these are facts to write from, not text to paste. Some commit
bodies mention our fork's context; the squash commit takes the owner's description instead.)

### test(python): exercise FaaS rules with an unavailable ambient store


### fix(python): isolate the FaaS test fixture from the ambient store

## Evidence
- In our Pants build (dspot-company-data runs it daily); not run on upstream main here (no Rust toolchain on this host).
