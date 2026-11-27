# test-shards-by-duration: facts for the owner's upstream PR

- **Branch:** DSpotDevelopers/pants `upstream-prep/test-shards-by-duration` at `74e78d1d5`, on `pantsbuild/pants main 83e5bf9f0`. Our patch: new (after +dspot.16).
- **Files:** `docs/notes/2.35.x.md`, `src/python/pants/core/goals/test.py`, `src/python/pants/core/goals/test_test.py`, `src/python/pants/core/util_rules/sharding.py`, `src/python/pants/core/util_rules/sharding_test.py`.
- **Tests:** `src/python/pants/core/goals/test_test.py`, `src/python/pants/core/util_rules/sharding_test.py`. Run: `pants test src/python/pants/core/goals/test_test.py src/python/pants/core/util_rules/sharding_test.py`.
- **Release note:** in the branch, `docs/notes/2.35.x.md`, "### Goals".
- **Disclosure (upstream requires it):** the code and tests were written by an LLM agent (Claude, Claude Code) and reviewed on our fork by our review lines; the owner reviews and tests it before opening.
- **Notes:** A feature: upstream may want an issue and a design note first (contribution guide: share the plan for a new feature).

## Feedback applied
- F4: note names both new options
- F7
- F3: assignment is deterministic for the same history on every shard
- F1: every added comment read (27 Nov 18:50Z); they say why

## What the owner's description needs
(Facts to write from: upstream requires a human-written title and description.)
- **Problem:** `--shard=k/N` assigns targets by address hash, so one shard can draw the most expensive tests and run far longer than the others (a 120-minute cut-off lost 283 results in one shard of ours).
- **Change:** New `[test].shard_timings` (historical seconds by address, `@file.json`): complete test batches are assigned longest-time-first to the least-loaded shard, deterministically for the same history; new addresses are estimated at the largest recorded time; an empty dictionary keeps hashing. New `[test].shard_timings_output` writes the run's measured seconds.
- **Tests:** `core/util_rules/sharding_test.py` (assignment, determinism, input order) and `core/goals/test_test.py`.

## Evidence
- In our Pants build (dspot-company-data runs it daily); not run on upstream main here (no Rust toolchain on this host).
