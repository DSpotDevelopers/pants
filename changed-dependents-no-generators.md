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

## What the owner's description needs: the facts, from the branch's own commits
(Upstream requires a human-written title and description: these are facts to write from, not text to paste. Some commit
bodies mention our fork's context; the squash commit takes the owner's description instead.)

### fix(vcs): `--changed-dependents` never selects a dependent's target generator

`find_changed_owners` drops the changed owners' target generators (#15313): a generator
depends on every target it generates, so keeping it makes all its siblings look changed.
A dependent's generator was kept: when one generated target of another generator is a
transitive dependent, that generator was selected too, and `test` then ran every one of
its siblings. In DSpot's company repository a one-file plugin change selected about 250
real dependents and expanded to 1,477 test files (871 from one tests generator).

The same rule now covers dependents: their generators leave the result, except one that
is itself a direct owner (a deleted generated file), as before.

Test: changed_integration_test test_change_dependent_in_another_generator; against
2.33.2 it lists //:other, with this change it does not.

(cherry picked from commit 97887f08ba144945f672025515cb4f94dc4ddfc8)

### style(vcs): ruff format the dependents expression in changed.py

What broke: the release PR's tests job (run 44893606494, job
136817536914) failed only 'ruff format': the --changed-dependents fix
(c19349874) left one expression past the line limit; every test passed.

The expression is formatted as ruff formats it; no behaviour changes.

Control: ruff format --check on changed.py and changed_integration_test.py
passes (it failed on changed.py at 086790464f); ruff check passes.


### test(vcs): a deleted file's dependent selects its own target, not its generator

What broke: the release PR's tests job (run 44905956541, job 136857621634)
failed test_deleted_file. It still expected src/python/top:tests, the
generator of the dependent bar_test.py:tests, which the
--changed-dependents fix (c19349874) deliberately no longer selects: a
dependent's generator leaves the result unless it is itself a direct owner
(the deleted file's own generator, top:top, which stays). The fix's commit
added test_change_dependent_in_another_generator but left this upstream
expectation at the old behaviour.

The expectation now lists what the rule selects; the job's own output shows
exactly bar.py, bar_test.py:tests and top:top.

Control: ruff format --check and ruff check pass. The integration test runs
in this PR's tests job (it needs a 2.33.2 engine this host lacks).


### docs: release note for --changed-dependents and target generators

## Evidence
- In our Pants build (dspot-company-data runs it daily); not run on upstream main here (no Rust toolchain on this host).
