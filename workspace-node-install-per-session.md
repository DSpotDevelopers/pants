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
- F1: not yet read line by line for comment style; the owner's review, or ours before he opens it

## What the owner's description needs: the facts, from the branch's own commits
(Upstream requires a human-written title and description: these are facts to write from, not text to paste. Some commit
bodies mention our fork's context; the squash commit takes the owner's description instead.)

### test(javascript): expose workspace tests running without their installed packages

In a workspace environment a test reads its package's node_modules from the checkout,
and the install that writes them is cached like a sandboxed one: a new checkout under
a warm process cache skips it, and the test finds no node_modules ("Local package.json
exists, but node_modules missing"). The cell installs a linked dependency, removes
node_modules as a new checkout would have none, and runs the test in a new session.


### fix(javascript): install workspace Node.js projects in every session

Patch 9 gave workspace test results the environment's session cache policy, but not
the install they read. In a workspace environment the install's result is the
project's node_modules in the checkout, which processes read in place; reusing it
from the process cache leaves a new checkout with none. There the project is now
installed once per session, as one install of the whole project (its packages share
one node_modules tree, and concurrent per-package installs into it race). Sandboxed
environments keep the cached per-package install and its node_modules digest.
Retest: the new workspace cell passes; test_integration_test.py and
install_node_package_test.py pass in full; lint passes.


### docs: release note

## Evidence
- In our Pants build (dspot-company-data runs it daily); not run on upstream main here (no Rust toolchain on this host).
