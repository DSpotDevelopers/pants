# changed-dependents-no-generators: facts for the owner's upstream PR

- **Branch:** DSpotDevelopers/pants `upstream-prep/changed-dependents-no-generators` at `7492dc516`, on `pantsbuild/pants main 83e5bf9f0`. Our patch: 11 (fork #20/#24).
- **Files:** `docs/notes/2.35.x.md`, `src/python/pants/vcs/changed.py`, `src/python/pants/vcs/changed_integration_test.py`.
- **Tests:** `src/python/pants/vcs/changed_integration_test.py`. Run: `pants test src/python/pants/vcs/changed_integration_test.py`.
- **Release note:** in the branch, `docs/notes/2.35.x.md`, "### Goals".
- **Disclosure (upstream requires it):** the code and tests were written by an LLM agent (Claude, Claude Code) and reviewed on our fork by our review lines; the owner reviews and tests it before opening.
- **Notes:** none

## Feedback applied
- F4: note links #15313, the rule this extends
- F1: the one comment says why a generator is no change
- F7

## What the owner's description needs
(Facts to write from: upstream requires a human-written title and description.)
- **Problem:** `--changed-dependents=transitive` selects a dependent's target generator: a generator depends on every target it generates, so it is a transitive dependent of each, and selecting it pulls in all its siblings (every file of a `python_tests` when one of them depends on the change). #15313 already drops the changed owners' generators.
- **Change:** The dependents' generators are dropped the same way, except one that is itself a direct owner (a deleted file's).
- **Tests:** `changed_integration_test.py::test_change_dependent_in_another_generator`, and the deleted-file case.

## Evidence
- In our Pants build (dspot-company-data runs it daily); not run on upstream main here (no Rust toolchain on this host).
