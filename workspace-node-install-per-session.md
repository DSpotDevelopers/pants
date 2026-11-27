# workspace-node-install-per-session: facts for the owner's upstream PR

- **Branch:** DSpotDevelopers/pants `upstream-prep/workspace-node-install-per-session` at `c54eb2001`, on `pantsbuild/pants main 83e5bf9f0`. Our patch: 10 (fork #6), follows patch 9.
- **Files:** `docs/notes/2.35.x.md`, `src/python/pants/backend/javascript/goals/test_integration_test.py`, `src/python/pants/backend/javascript/install_node_package.py`.
- **Tests:** `src/python/pants/backend/javascript/goals/test_integration_test.py`. Run: `pants test src/python/pants/backend/javascript/goals/test_integration_test.py`.
- **Release note:** in the branch, `docs/notes/2.35.x.md`, "#### Javascript".
- **Disclosure (upstream requires it):** the code and tests were written by an LLM agent (Claude, Claude Code) and reviewed on our fork by our review lines; the owner reviews and tests it before opening.
- **Notes:** Applies alone on main, but describes itself as patch 9's follow-up: open it after js-test-environments.

## Feedback applied
- F4
- F7
- F1: every added comment read (27 Nov 18:50Z); they say why

## What the owner's description needs
(Facts to write from: upstream requires a human-written title and description.)
- **Problem:** In a workspace environment a Node.js project's install writes `node_modules` into the checkout, but the install is cached like a sandboxed one: a new checkout under a warm process cache skips it and the test fails with "Local package.json exists, but node_modules missing".
- **Change:** In a workspace environment the project is installed once per session, as one install of the whole project (its packages share one `node_modules` tree; concurrent per-package installs race). Sandboxed environments keep the cached per-package install.
- **Tests:** A workspace case that removes `node_modules` as a new checkout would and runs the test in a new session (`test_integration_test.py`).

## Evidence
- In our Pants build (dspot-company-data runs it daily); not run on upstream main here (no Rust toolchain on this host).
