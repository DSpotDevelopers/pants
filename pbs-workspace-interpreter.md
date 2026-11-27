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
- F1: every added comment read (27 Nov 18:50Z); they say why

## What the owner's description needs
(Facts to write from: upstream requires a human-written title and description.)
- **Problem:** In a workspace environment (`experimental_workspace_environment`) the python-build-standalone provider extracts its interpreter archive by a sandbox-relative path, which the build root does not hold, so a `python_tests` with `environment="workspace"` gets no interpreter.
- **Change:** In a workspace environment the archive is downloaded and extracted in the local environment (the same bytes, the same host and platform), and installed from the process's inputs.
- **Tests:** `python_build_standalone/rules_test.py`: a workspace-environment interpreter installs.

## Evidence
- In our Pants build (dspot-company-data runs it daily); not run on upstream main here (no Rust toolchain on this host).
