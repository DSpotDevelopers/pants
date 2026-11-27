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
- F1: not yet read line by line for comment style; the owner's review, or ours before he opens it

## What the owner's description needs: the facts, from the branch's own commits
(Upstream requires a human-written title and description: these are facts to write from, not text to paste. Some commit
bodies mention our fork's context; the squash commit takes the owner's description instead.)

### test(javascript): expose missing workspace test environments

Control: JS, TypeScript and TSX test targets reject environment=workspace (three red cells).

Add execution coverage for selected files, workspace reads and cross-session result invalidation.

Retest the focused JS test rules and native workspace runner after wiring the environment fields.

### fix(javascript): retain test environments and bootstrap sandbox paths

JS test field sets discarded environment choice and forced prepared-runtime tests into a sandbox.
Carry environment fields through JS, TypeScript and TSX targets and generators.
Keep archive/Corepack paths inside their input sandbox and honor environment result-cache policy.
Controls: three field reds; stale-result and missing-bootstrap-input mutations both fire.
Retest: focused Pants JS/Node suites, workspace runner, archive extraction and Ruff.

### fix(workspace tests): drop formatting churn; AST and lint retest


### docs: release note

## Evidence
- In our Pants build (dspot-company-data runs it daily); not run on upstream main here (no Rust toolchain on this host).
