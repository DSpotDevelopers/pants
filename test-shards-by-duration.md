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
- F1: not yet read line by line for comment style; the owner's review, or ours before he opens it

## What the owner's description needs: the facts, from the branch's own commits
(Upstream requires a human-written title and description: these are facts to write from, not text to paste. Some commit
bodies mention our fork's context; the squash commit takes the owner's description instead.)

### test(test): reproduce duration-blind native sharding

The whole-scope run loses 283 results when one address-hash shard reaches its 120-minute cutoff. Prove that measured durations must choose native batches, retain every batch once, and report execution time for the next observation. The native goal control fails on the base because it executes all four batches instead of the requested duration-balanced half.

### feat(test): balance native shards by measured process time

Keep the graph and backend batches as the population, then assign whole batches longest-time-first using the same historical durations on every shard. New tests remain included with a conservative estimate. Record actual process seconds for the next observation rather than workunit queueing time. The existing address hash remains the unconfigured behavior.

Validation: the native duration-shard regression fails on the preceding commit; normal source Pants lint and both focused suites pass on this tree, as does tailor --check. Real CLI shards consume the timing JSON and produce disjoint execution-time reports.

### docs: release note

## Evidence
- In our Pants build (dspot-company-data runs it daily); not run on upstream main here (no Rust toolchain on this host).
