# DSpot's Pants build

This is official Pants **2.33.2** plus the reviewed fixes below. Every fix has a documented exit.
Upstream submission is optional and belongs only to the owner; it is not a build or approval gate.
Apart from the version label and this file, nothing else differs from the `release_2.33.2` tag.

Version: `2.33.2+dspot.13`. A repository pins it like any Pants version: `pants_version = "2.33.2+dspot.13"` in
`pants.toml`. The stock scie-pants launcher fetches it through `PANTS_BOOTSTRAP_URLS`, set in the repository's
committed `.pants.bootstrap`. There's no wrapper script.

| # | Patch (commits on this branch) | Review / upstream status | Exit |
|---|---|---|---|
| 1 | Install the transitive dependencies of pnpm workspace packages: upstream's own change, byte for byte (`nodejs_project_environment.py`, `package_manager.py` and both tests; its `docs/notes/2.35.x.md` entry is left out) | pantsbuild/pants#23754, merged on 2026-11-16 as `32a5115f0bc752b48501a78b3824b9bef1465235`; cherry-picked here in `+dspot.11` in place of our earlier copy, which reached the same behaviour by its own pnpm-only branch | Drops by itself at the first upstream pin that contains `32a5115f0` (it is on main, not on the 2.34.x branch: 2.35). |
| 2 | JS inference finds the owner of an imported non-module file, such as `./x.css` or `./rows.json` | Branch `dspot/js-infer-non-js-files` on this fork, on Pants main; the issue and PR are posted by a person (Pants requires human-written text) | Drop it when a Pants release we pin contains the upstream fix. |
| 3 | JS inference reads a bundler query's file: `./App.tsx?raw`, `./logo.svg?url` | Branch `dspot/js-infer-bundler-query` (on patch 2's), posted the same way | Drop it when a Pants release we pin contains the upstream fix. |
| 4 | A TypeScript `.js` specifier infers the source it compiles from: `./errors.js` -> `errors.ts`/`.tsx`/`.d.ts`, `./View.jsx` -> `View.tsx` | Branch `dspot/js-infer-ts-js-specifier` (on patch 3's), posted the same way | Drop it when a Pants release we pin contains the upstream fix. |
| 5 | TypeScript check keeps the repository-root Node project and a sandbox-relative root wrapper path (`9b4d1aed7`, `cfe58a301`) | Root-project support retained; subfolder projects use stock resolve lookup and unnamed package targets | Drop it when a Pants release we pin contains equivalent root-project/root-wrapper support. |
| 6 | Preserve TypeScript compiler inputs: imported JavaScript | DSpotDevelopers/pants#2, approved at `3fcae484e9`, and #3 (no snapshot of the installed resolve in config discovery), approved at `097d64486b`; upstream's 2.34 branch hydrates the checked targets' transitive dependencies (`029bd904d`), which does not cover our case: a TypeScript source importing a pnpm workspace package of the same Node project (`@flowsev/plugin-sdk`) reaches that package's `package_json` target, not its JS and declaration sources. Tried in `+dspot.11`'s pull request: `pants check workflows/accountancy-processes/plugin::` on dspot-company-data went from 34 to 132 errors, the 98 new ones all TS2305 `Module '"@flowsev/plugin-sdk"' has no exported member …` | Keep it at the 2.34 pin unless upstream hydrates a workspace package's sources for its importers; re-run that check on the pin. Keep config-program selection under patch 7 until upstream provides it. |
| 7 | TypeScript check builds the configs owning the selected sources, with their declared project references, rather than every member of a Node resolve | DSpotDevelopers/pants#2, approved at `3fcae484e9`, and #3 (no snapshot of the installed resolve in config discovery), approved at `097d64486b`; coordinator/owner owns external review and submission | Drop it when a Pants release we pin separates TypeScript programs from Node resolves. |
| 8 | TypeScript check consumes generated and packaged data dependencies of its active tsconfigs; package-shell targets build through package, never source codegen; output validation matches captured names without walking dependency links | DSpotDevelopers/pants#4, approved at `576f692d81524e907570921aa28bedfb26430f3c`; upstream preparation is parked under the owner's correction | Drop it when a pinned Pants release carries equivalent generated config-input and package/source separation. |

| 9 | JS/TS/TSX tests select existing execution environments; workspace-safe cache policy, archive extraction and Corepack paths | DSpotDevelopers/pants#5, approved at `455825ce1e72db3777a24e7d7aa6b62de12acadb` | Unblocks Pipeline 200 criterion 4; drop when a pinned upstream release provides equivalent execution-environment, bootstrap-path and cache behavior. |
| 10 | In a workspace environment, a Node.js project is installed into the checkout once per session (one install of the project, never reused from the process cache), so a new checkout under a warm cache still gets its node_modules | This branch's follow-up to patch 9 (its PR on this fork) | Drop it with patch 9, when a pinned upstream release installs workspace-environment Node.js projects per session. |
| 11 | `--changed-dependents` never selects a dependent's target generator: upstream drops the changed owners' generators (pantsbuild/pants#15313), and this applies the same rule to the dependents' generators, except one that is a direct owner (a deleted generated file); `changed_integration_test.py::test_change_dependent_in_another_generator` | DSpotDevelopers/pants#20, approved at `97887f08ba144945f672025515cb4f94dc4ddfc8`, merged to this fork's main as `a87bb3f648` | Drop it when a pinned upstream release excludes dependents' target generators from `--changed-dependents`. |
| 12 | In a workspace environment, the python-build-standalone provider installs its interpreter from the process sandbox's inputs, never from checkout-relative paths the workspace does not hold, so a `python_tests` with `environment="workspace"` gets its interpreter; `python_build_standalone/rules_test.py` | DSpotDevelopers/pants#19, approved at `b6d91e1971`, merged to this fork's main as `1d66212c47` | Drop it when a pinned upstream release installs python-build-standalone interpreters in a workspace environment. |
| 13 | A stylesheet's links infer their targets: `@import "@flowsev/design"` (a trailing `theme(...)` or `layer(...)` aside) and Tailwind's `@source "@flowsev/ui"` infer the package's node target, as a JavaScript import of the package does; `@import "./tokens.css"` infers the file's owner, and a relative link to a package's folder (Tailwind's `@source "../ui"`) that package; links resolve from the stylesheet's own folder, whichever target owns it; `@source not` links nothing. It reads the `.css` source of a `file` or `resource` target (`dependency_inference/rules.py`, `infer_stylesheet_dependencies`; eight cells in `rules_test.py`) | This fork's pull request; upstream submission optional and the owner's | Drop it when a Pants release we pin infers stylesheet `@import`/`@source` links. |
| 14 | `ruff check` also lints the `.py` files of `file` and `resource` targets when `[ruff].check_python_assets` is set (default off: stock behaviour). It is a second lint request under the same `ruff-check` id, so `--only=ruff-check` runs both, with the same Ruff, config and report; `skip_ruff_check` / `skip_ruff` are also accepted on `file`/`resource` targets (`ruff/check/rules.py`, `RuffLintPythonAssetsRequest`; six cells in `ruff/rules_integration_test.py`) | This fork's pull request; upstream submission optional and the owner's | Drop it when a Pants release we pin lints Python files owned by `file`/`resource` targets, or when no repository pinning this build sets `check_python_assets` (its Python read as data all owned by Python targets). |
| 15 | Each Pants process starts its own sandboxer on its own socket (`sandboxer-<pid>.sock`), never one socket path shared by every Pants process of a buildroot; a sandboxer killed mid-read releases its LMDB reader slots. Upstream's commit, applied unchanged but for its 2.34 release note (`sandboxer/src/lib.rs`, `sharded_lmdb/src/lib.rs`, `sandboxer/tests/integration_test.rs`) | pantsbuild/pants#23720 (fixes #23716), merged upstream as `88f57cf3e`, released in 2.34.0a0 | Drop it when the pinned upstream release is 2.34.0 or later. |
| 17 | Each `Sandboxer` gets its own socket, `sandboxer-<pid>-<n>.sock` (`n` counts the Sandboxers its process has created), never one socket per process: pantsd builds a new scheduler, and so a new Sandboxer, when its options change, while the old one's server still runs, and the two shared patch 15's `sandboxer-<pid>.sock`, so the new client could reach the old server and lose it mid-request ("materialize_directory() request to sandboxer process failed: transport error"; company main, app-tests 1/4, job 139571655427). (`sandboxer/src/lib.rs`, `sandboxer/src/tests.rs`) | DSpot's own; upstream 2.34 carries patch 15's per-process name, so the same defect: any upstream report is the owner's | Drop it with patch 15 when the pinned upstream release names each Sandboxer's socket on its own. |

JSON compiler inputs use stock `file` targets with explicit dependencies. The compiler no longer
collects `resource` targets as JSON inputs; the existing file-target compiler test covers this path.
Module-specific declarations use stock `file` targets and explicit dependencies too. TypeScript and TSX
default globs and module-extension inference no longer carry the module-specific additions.
Package exports keep stock runtime-source inference. Declaration sources use ordinary TypeScript
ownership; exported data uses the stock `package_json(dependencies=[...])` field.
Static tsconfig data uses the same stock file dependency path. Patch 8 collects generated sources and
packages only; it no longer stages static file/resource data reached solely through a config owner.
Subfolder TypeScript project roots use unnamed `package_json()` targets and stock resolve lookup.
The repository-root case retains its discovered resolve and relative wrapper path: the stock empty-path
lookup and leading-slash wrapper filename do not provide a working root-project path in this release.

## Rules for this branch

- Fixes are reviewed on this fork and recorded above with their removal conditions. The owner clarified on
  2026-11-12 that an open upstream PR is not required. Only the owner may submit or discuss changes upstream.
- `+dspot.2` is the same source as `+dspot.1`, rebuilt with only the version label changed, so it can be published as an
  immutable release (immutable releases were enabled on this fork after `+dspot.1` was published). `+dspot.3` adds
  patches 3 and 4; `+dspot.4` adds patch 5; `+dspot.5` adds patches 6 and 7; `+dspot.6` corrects them (#3: config
  discovery inventories sources and configs, never the installed resolve's links). `+dspot.7` adds patch 8
  from the approved config-input and package/output-validation fix. `+dspot.8` adds patch 9; `+dspot.9` adds patch 10; `+dspot.10` adds patches 11 and 12. `+dspot.11` replaces patch 1 with upstream's merged #23754 (owner, 16 Nov: where Pants already has a way, we use theirs); patch 6 stays, as its row says why. `+dspot.12` adds patch 13; `+dspot.13` adds patch 14. Every release from `+dspot.2` on is
  immutable: the launcher can't check the PEX's hash.
- When a patch's upstream PR is released, the next build drops it and bumps the `+dspot.N` label. When none is left,
  repositories go back to the plain official version and this branch is retired.
- Building:
  - use Pants' own release steps (`.github/workflows/release.yaml`: `release.py build-wheels`, then
    `package src/python/pants:pants-pex`) with `VERSION` set to the label above, on our own machines, never on
    GitHub-hosted runners. Every native file is linked against glibc 2.28 (the manylinux_2_28 floor), not in the
    manylinux container, which our runners refuse: `build-support/bin/dspot_release_build.sh`, run by the build job
    of the default branch's `dspot-pants.yaml` (a `pull_request_target` run reads its workflow from `main`, never
    from this branch; the script comes from the pull request's head), links them through zig's 2.28 stubs, and
    `dspot_glibc_floor.py` refuses the release when any native file of its wheel or PEX needs a newer glibc;
  - the artifacts' names follow the official ones, `pants.<version>-cp314-<platform>.pex`.

## Source for this build

- Official base: `release_2.33.2`.
- Patches 1–5 are unchanged from immutable `2.33.2+dspot.4` (`835b8525b1`).
- Patches 6 and 7 are immutable `2.33.2+dspot.5`'s source (DSpotDevelopers/pants#2 at `3fcae484e9`, release commit
  `f8b6420a97`) plus DSpotDevelopers/pants#3 at `097d64486b`: its red control (`e4622b2c0`) and fix (`097d64486`),
  which inventory the source/config query input instead of snapshotting the prepared process's installed resolve
  (the pnpm workspace link cycle).
- Patch 8 was merged as `1c86a5a475cfe98fba5e0b6bfdc2c241010b089e` and is the approved source of DSpotDevelopers/pants#4 at `576f692d81524e907570921aa28bedfb26430f3c`:
  selected config data and package inputs, package/source separation and link-safe output validation.
- Patch 9 was merged as `4795dd5e5a49f350ddf9b6d7716e2e0cd086a1b7` (DSpotDevelopers/pants#5).
- Patch 10 was merged as `0ddb1517a9339087227fd4fa7dcb414b7c420a71` and is the approved source of DSpotDevelopers/pants#6 at `d58ac2fc71503d15ea6a9c8aaa079f04e2bd1977`:
  a workspace environment installs its Node.js project once per session.
- Patch 11 came with DSpotDevelopers/pants#24 (`c19349874`, and `0a1a1c035`'s formatting): DSpotDevelopers/pants#20's change,
  approved at `97887f08ba` and merged to this fork's main as `a87bb3f648`.
- Patch 12 is DSpotDevelopers/pants#19, merged as `1d66212c47`, cherry-picked here (`-m 1 -x`): the provider's rules and their test.
- `+dspot.11` takes upstream's way for patch 1 (owner DM 1034404, 16 Nov): its files are upstream's `32a5115f0` (pantsbuild/pants#23754). Patch 6 was tried with upstream 2.34.x's transitive hydration and kept: row 6 names the failing case.
- Patch 13 is this fork's stylesheet-link inference (`+dspot.12`): the company's app lane selects an app when a design
  library it styles itself with changes, which stock inference cannot see (it reads JavaScript and TypeScript only).
- Patch 14 is this fork's Ruff check of Python assets (`+dspot.13`): the company lints every tracked `.py` file, and 76
  of them are fixtures and other Python owned only by `file`/`resource` targets, which stock `ruff check` skips. Without
  it that lint stays a CI step outside Pants (`git ls-files '*.py' | xargs ruff check`).
- This release commit changes only this record and `src/python/pants/VERSION`.
- `+dspot.10` is built by `.github/workflows/dspot-pants.yaml` on the pull request that adds this line: its `build` job runs
  the release steps above on our `dspot` runner and keeps the wheels and PEX as the run's `release-<head>` artifact,
  which is what gets published. Pull requests our worker lines open can start it since DSpotDevelopers/pants#28.
  #30's own run linked its natives against the runner's glibc 2.39 (`native_engine.so` named GLIBC_2.39), so its
  artifact was not published; the first run with the glibc 2.28 build is the one that is. DSpotDevelopers/pants#31
  changed only this branch's copy of the workflow, so the first run on the pull request that adds this line
  (45048880245) still ran `main`'s old build step: no zig, no floor check, and its natives named GLIBC_2.39, so it was
  not published either. The release is that pull request's run after DSpotDevelopers/pants#33 put the build on
  `main`: its head is `+dspot.10`'s release source. It changes this record, the workflow test's account of where the
  workflow comes from, and where the build script keeps its zig wrappers: its first run linked every native file at
  GLIBC_2.28 but wrote the wrappers into `build-support/bin/rust`, whose files the engine hash covers, so the tests job
  (a checkout without them) rebuilt the engine it was handed and failed. They live in the runner's temp folder now.

## JavaScript test execution environments (patch 9)

DSpotDevelopers/pants#5 was approved at `455825ce1e72db3777a24e7d7aa6b62de12acadb` and merged with a
merge commit at `4795dd5e5a49f350ddf9b6d7716e2e0cd086a1b7`. JavaScript, TypeScript and TSX tests and
their generators carry the existing execution environment into the stock test goal. Workspace results use
that environment's session cache policy, and archive extraction and Corepack preparation address their
sandbox inputs and outputs even when commands execute in the checkout. The package test script still receives
exactly the selected files.

This unblocks Pipeline 200 criterion 4 (BUILD files not from tailor): ordinary tailor-generated test targets can
replace handwritten test-as-source declarations and folder-runner inventories once this build is consumed.
Remove patch 9 when a pinned Pants release provides equivalent test-environment selection, sandbox bootstrap
paths and workspace result-cache behavior. Only the owner controls upstream submission.

This release adds patch 9 to immutable `2.33.2+dspot.7`. Its Rust and native-bootstrap source trees are
unchanged, so the four native binaries are reused byte for byte from that release's checksum-verified PEX.
The Python distribution and PEX are built from this source using stock Pants packaging targets.

## Workspace installs (patch 10)

Patch 9 gave workspace test results the environment's session cache policy, but not the install those tests read.
There the install's result is the project's `node_modules` in the checkout, which processes read in place, so a
cached install skipped in a new checkout leaves the tests with no `node_modules`. In a workspace environment the
project is now installed once per session, as one install of the whole project: every package of a project shares
its `node_modules` tree, and concurrent per-package installs into one tree race. Sandboxed environments keep the
cached per-package install and its captured `node_modules` digest unchanged.

## Buildbarn from containerized jobs

Buildbarn's test stacks copy their configuration and empty state directories into project-scoped
Docker volumes. An owned relay reaches the services on their Compose network over Docker exec;
only the test process listens locally. No daemon-host directory or published port is used.
Remove this patch when the pinned upstream stack supports a separate Docker daemon this way.

## Docker sandbox archive transfer

The Docker executor's archive helper stages each returned sandbox before replacing local inputs,
retaining modes and symlinks without overwriting hard-linked CAS data. It refuses foreign roots,
special files and traversal outside staging. Its caller copies the complete declared digest into a per-container sandbox volume and copies
outputs back before local capture. Named caches remain a separate persistent volume; shutdown and
stale-container removal delete only the disposable sandbox volume. Retained-sandbox replay also
uses copy I/O and writes replay outputs beside the original, preserving its input links.
Remove both parts when a pinned upstream executor supports a separate daemon through volume/copy I/O.
