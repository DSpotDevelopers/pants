# pbs-workspace-interpreter: facts for the owner's upstream PR

- **Branch:** DSpotDevelopers/pants `upstream-prep/pbs-workspace-interpreter` at `7391d0e3d`, on `pantsbuild/pants main 83e5bf9f0`. Our patch: 12 (fork #19).
- **Files:** `docs/notes/2.35.x.md`, `src/python/pants/backend/python/providers/python_build_standalone/rules.py`, `src/python/pants/backend/python/providers/python_build_standalone/rules_test.py`.
- **Tests:** `src/python/pants/backend/python/providers/python_build_standalone/rules_test.py`. Run: `pants test src/python/pants/backend/python/providers/python_build_standalone/rules_test.py`.
- **Release note:** in the branch, `docs/notes/2.35.x.md`, "#### Python".
- **Disclosure (upstream requires it):** the code and tests were written by an LLM agent (Claude, Claude Code) and reviewed on our fork by our review lines; the owner reviews and tests it before opening.
- **Notes:** none

## Feedback applied
- F4
- F7
- commit message rewritten without our fork's merge text
- F1: not yet read line by line for comment style; the owner's review, or ours before he opens it

## What the owner's description needs: the facts, from the branch's own commits
(Upstream requires a human-written title and description: these are facts to write from, not text to paste. Some commit
bodies mention our fork's context; the squash commit takes the owner's description instead.)

### python-build-standalone: install the interpreter from sandbox inputs in a workspace environment

In a workspace environment the provider installed its interpreter from
paths relative to the checkout, which the workspace does not hold, so a
`python_tests` target with `environment="workspace"` had no interpreter.
It now installs from the process sandbox's own inputs.

### docs: release note

## Evidence
- In our Pants build (dspot-company-data runs it daily); not run on upstream main here (no Rust toolchain on this host).
