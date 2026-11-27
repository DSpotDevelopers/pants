# Upstream texts for our Pants patches: facts for the owner's own PR descriptions

Upstream Pants' contribution policy (docs/docs/contributions/index.mdx, "LLM Assistance Notice", on main 83e5bf9f0):
AI-assisted code is welcome when disclosed, but "All community interactions, including comments, discussion, issues,
PR titles, and descriptions *must be composed by a human*." So each file here is not a text to paste: it is the
facts, the evidence and the disclosure the owner's own title and description need. The branch is the code.

- Branches live on our fork only (DSpotDevelopers/pants, `upstream-prep/<name>`), each based on pantsbuild/pants main
  83e5bf9f0 (26 Nov 2026). No upstream PR, issue or comment was opened; only the owner opens one (rule 44).
- Upstream squash-merges: the description becomes the changelog entry.
- Release notes go in the version under development, `docs/notes/2.35.x.md`.
- Tests: the patches' tests pass on our 2.33.2 build (its qualification). On upstream main they were not run here,
  because this host has no Rust toolchain to build upstream's engine. Upstream's CI runs them when the PR is opened.
  Each file names the exact test command.

Reviewer feedback upstream already gave on similar changes, applied where it fits (each file says which):
- F1, #22461 (tobni, benjyw): comments explain why, never restate the code; no long docstrings or READMEs.
- F2, #22461 (tobni): rules call each other by name (call-by-name), not `Get`.
- F3, #22461 (tobni): `OrderedSet` where order matters; type-check what the command line selects, not whole projects.
- F4, #22756 (tobni) and #23754 (benjyw): the release note in the current notes file, worded as what it is (a fix or
  a feature), linked to its issue.
- F5, #23754 (benjyw): package-manager-specific logic lives in `PackageManager`.
- F6, #23075 (benjyw, tdyas): names that explain; tuples in frozen fields; Rust logic out of macro bodies.
- F7, upstream policy: disclose how much an LLM wrote; a human writes the title and description.

## The table

| patch | branch (DSpotDevelopers/pants) | facts file | feedback applied | state |
|---|---|---|---|---|
| 2: non-module imports | `upstream-prep/js-infer-non-js-files` 6e759ecba | js-infer-non-js-files.md | F1 (read), F4 (note moved 2.34 -> 2.35), F7 | ready for the owner |
| 3: bundler query (on 2) | `upstream-prep/js-infer-bundler-query` 272b80fb5 | js-infer-bundler-query.md | F1 (read), F4, F7 | ready, after 2 |
| 4: TS `.js` specifier (on 3) | `upstream-prep/js-infer-ts-js-specifier` c6af81137 | js-infer-ts-js-specifier.md | F1 (read), F4, F7 | ready, after 3 |
| 13: stylesheet links (on 4) | `upstream-prep/stylesheet-links` 681b2ea46 | stylesheet-links.md | F2, F4, F7 | ready, after 4 |
| 11: --changed-dependents generators | `upstream-prep/changed-dependents-no-generators` 7492dc516 | changed-dependents-no-generators.md | F1 (read), F4 (links #15313), F7 | ready |
| 14: ruff on file/resource .py | `upstream-prep/ruff-check-python-assets` d483333f0 | ruff-check-python-assets.md | F4, F7 | ready; docs page maybe asked |
| 17: Sandboxer socket per instance | `upstream-prep/sandboxer-socket-per-sandboxer` 8c21fe964 | sandboxer-socket-per-sandboxer.md | F4, F6, F7 | ready; Rust not compiled here |
| 12: PBS in a workspace | `upstream-prep/pbs-workspace-interpreter` 7391d0e3d | pbs-workspace-interpreter.md | F4, F7, clean commit message | ready |
| 9: JS/TS test environments | `upstream-prep/js-test-environments` 48fd91021 | js-test-environments.md | F4, F5, F7 | ready |
| 10: workspace Node install per session | `upstream-prep/workspace-node-install-per-session` c54eb2001 | workspace-node-install-per-session.md | F4, F7 | ready, after 9 |
| shard by measured time | `upstream-prep/test-shards-by-duration` 74e78d1d5 | test-shards-by-duration.md | F3, F4, F7 | ready; a feature: issue first |
| #43 backend test fixtures | `upstream-prep/backend-test-fixture-assumptions` 05b1aec53 | backend-test-fixture-assumptions.md | F7 | ready (tests) |
| FaaS test fixture | `upstream-prep/faas-test-ambient-store` 3d88d9f29 | faas-test-ambient-store.md | F7 | ready (tests) |
| JS test fixture reuse | `upstream-prep/js-test-fixture-tool-reuse` 3bc73a73b | js-test-fixture-tool-reuse.md | F7 | ready (tests) |
| Buildbarn tests in containers | `upstream-prep/buildbarn-relay-containerized-jobs` 9d695d354 | buildbarn-relay-containerized-jobs.md | F7 | ready (test infra) |
| #48 lint summary order | `upstream-prep/lint-summary-test-order` 279cdb705 | lint-summary-test-order.md | F7 | ready (test) |
| Docker archive staging | `upstream-prep/docker-archive-staging` ded282e6f | docker-archive-staging.md | F7 | open with #53/#54 |
| 5-8: TypeScript check (root project, selected configs, config data) | not prepared | - | (F3 is tobni's own ask on #22461: check what is selected) | port needed: upstream's check.py changed since 2.33 (029bd904d hydration with codegen; #23505 `find_sh`); the semantic merge needs check_test on upstream main, and upstream will want 3 PRs |
| #53/#54 Docker sandbox volumes | not prepared | - | - | conflicts with upstream's docker.rs; both still open and unreviewed on our fork |
| 1 (#23754), 15 (#23720) | already upstream | - | - | none needed |
| #42, #46, #47 | not upstreamable | - | - | our fork's own CI workflow |
