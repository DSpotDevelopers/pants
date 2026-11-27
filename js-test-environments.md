# js-test-environments: facts for the owner's upstream PR

- **Branch:** DSpotDevelopers/pants `upstream-prep/js-test-environments` at `48fd91021`, on `pantsbuild/pants main 83e5bf9f0`. Our patch: 9 (fork #5).
- **Files:** `docs/notes/2.35.x.md`, `src/python/pants/backend/javascript/goals/test.py`, `src/python/pants/backend/javascript/goals/test_integration_test.py`, `src/python/pants/backend/javascript/goals/test_test.py`, `src/python/pants/backend/javascript/subsystems/nodejs.py`, `src/python/pants/backend/javascript/subsystems/nodejs_test.py`, `src/python/pants/backend/javascript/target_types.py`, `src/python/pants/backend/tsx/target_types.py`, `src/python/pants/backend/typescript/target_types.py`, `src/python/pants/core/util_rules/archive.py`, `src/python/pants/core/util_rules/archive_test.py`.
- **Tests:** `src/python/pants/backend/javascript/goals/test_integration_test.py`, `src/python/pants/backend/javascript/goals/test_test.py`, `src/python/pants/backend/javascript/subsystems/nodejs_test.py`, `src/python/pants/core/util_rules/archive_test.py`. Run: `pants test src/python/pants/backend/javascript/goals/test_integration_test.py src/python/pants/backend/javascript/goals/test_test.py src/python/pants/backend/javascript/subsystems/nodejs_test.py src/python/pants/core/util_rules/archive_test.py`.
- **Release note:** in the branch, `docs/notes/2.35.x.md`, "#### Javascript".
- **Disclosure (upstream requires it):** the code and tests were written by an LLM agent (Claude, Claude Code) and reviewed on our fork by our review lines; the owner reviews and tests it before opening.
- **Notes:** none

## Feedback applied
- F4
- F7
- F5: package-manager paths (Corepack) stay with the package manager
- F1: every added comment read (27 Nov 18:50Z); they say why

## What the owner's description needs
(Facts to write from: upstream requires a human-written title and description.)
- **Problem:** JavaScript, TypeScript and TSX test targets drop the `environment` field, so a test cannot choose, for example, a workspace environment; archive extraction and Corepack paths can point outside the input sandbox.
- **Change:** The environment field reaches the JS/TS/TSX test field sets and generators, results follow the environment's cache policy, and archive/Corepack paths stay inside their input sandbox.
- **Tests:** Three red cases (each target type with `environment="workspace"`) and execution cases in `javascript/goals/test_integration_test.py` and `test_test.py`.

## Evidence
- In our Pants build (dspot-company-data runs it daily); not run on upstream main here (no Rust toolchain on this host).
