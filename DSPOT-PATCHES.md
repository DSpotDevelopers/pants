# DSpot's Pants build

This is official Pants **2.33.2** plus the reviewed fixes below. Every fix has a documented exit.
Upstream submission is optional and belongs only to the owner; it is not a build or approval gate.
Apart from the version label and this file, nothing else differs from the `release_2.33.2` tag.

Version: `2.33.2+dspot.10`. A repository pins it like any Pants version: `pants_version = "2.33.2+dspot.10"` in
`pants.toml`. The stock scie-pants launcher fetches it through `PANTS_BOOTSTRAP_URLS`, set in the repository's
committed `.pants.bootstrap`. There's no wrapper script.

| # | Patch (commits on this branch) | Review / upstream status | Exit |
|---|---|---|---|
| 1 | Install the transitive dependencies of pnpm workspace packages (its test and fix commits; the PR's 2.34 docs commit is left out) | pantsbuild/pants#23754 merged on 2026-11-16 as `32a5115f0bc752b48501a78b3824b9bef1465235` | Remove our copy at the next upstream version pin: 2.34 if its branch receives #23754 before the pin, otherwise 2.35. The measured 2.34 branch at `453ca656` does not yet contain its workspace-dependencies selector. |
| 2 | JS inference finds the owner of an imported non-module file, such as `./x.css` or `./rows.json` | Branch `dspot/js-infer-non-js-files` on this fork, on Pants main; the issue and PR are posted by a person (Pants requires human-written text) | Drop it when a Pants release we pin contains the upstream fix. |
| 3 | JS inference reads a bundler query's file: `./App.tsx?raw`, `./logo.svg?url` | Branch `dspot/js-infer-bundler-query` (on patch 2's), posted the same way | Drop it when a Pants release we pin contains the upstream fix. |
| 4 | A TypeScript `.js` specifier infers the source it compiles from: `./errors.js` -> `errors.ts`/`.tsx`/`.d.ts`, `./View.jsx` -> `View.tsx` | Branch `dspot/js-infer-ts-js-specifier` (on patch 3's), posted the same way | Drop it when a Pants release we pin contains the upstream fix. |
| 5 | TypeScript check keeps the repository-root Node project and a sandbox-relative root wrapper path (`9b4d1aed7`, `cfe58a301`) | Root-project support retained; subfolder projects use stock resolve lookup and unnamed package targets | Drop it when a Pants release we pin contains equivalent root-project/root-wrapper support. |
| 6 | Preserve TypeScript compiler inputs: imported JavaScript | DSpotDevelopers/pants#2, approved at `3fcae484e9`, and #3 (no snapshot of the installed resolve in config discovery), approved at `097d64486b`; upstream's 2.34 branch includes transitive compiler inputs | Remove the compiler-input copy at the next 2.34 pin, validating the focused compiler cases against upstream's transitive source hydration. Keep config-program selection under patch 7 until upstream provides it. |
| 7 | TypeScript check builds the configs owning the selected sources, with their declared project references, rather than every member of a Node resolve | DSpotDevelopers/pants#2, approved at `3fcae484e9`, and #3 (no snapshot of the installed resolve in config discovery), approved at `097d64486b`; coordinator/owner owns external review and submission | Drop it when a Pants release we pin separates TypeScript programs from Node resolves. |
| 8 | TypeScript check consumes generated and packaged data dependencies of its active tsconfigs; package-shell targets build through package, never source codegen; output validation matches captured names without walking dependency links | DSpotDevelopers/pants#4, approved at `576f692d81524e907570921aa28bedfb26430f3c`; upstream preparation is parked under the owner's correction | Drop it when a pinned Pants release carries equivalent generated config-input and package/source separation. |

| 9 | JS/TS/TSX tests select existing execution environments; workspace-safe cache policy, archive extraction and Corepack paths | DSpotDevelopers/pants#5, approved at `455825ce1e72db3777a24e7d7aa6b62de12acadb` | Unblocks Pipeline 200 criterion 4; drop when a pinned upstream release provides equivalent execution-environment, bootstrap-path and cache behavior. |
| 10 | In a workspace environment, a Node.js project is installed into the checkout once per session (one install of the project, never reused from the process cache), so a new checkout under a warm cache still gets its node_modules | This branch's follow-up to patch 9 (its PR on this fork) | Drop it with patch 9, when a pinned upstream release installs workspace-environment Node.js projects per session. |
| 11 | `--changed-dependents` never selects a dependent's target generator: upstream drops the changed owners' generators (pantsbuild/pants#15313), and this applies the same rule to the dependents' generators, except one that is a direct owner (a deleted generated file); `changed_integration_test.py::test_change_dependent_in_another_generator` | DSpotDevelopers/pants#20, approved at `97887f08ba144945f672025515cb4f94dc4ddfc8`, merged to this fork's main as `a87bb3f648` | Drop it when a pinned upstream release excludes dependents' target generators from `--changed-dependents`. |
| 12 | In a workspace environment, the python-build-standalone provider installs its interpreter from the process sandbox's inputs, never from checkout-relative paths the workspace does not hold, so a `python_tests` with `environment="workspace"` gets its interpreter; `python_build_standalone/rules_test.py` | DSpotDevelopers/pants#19, approved at `b6d91e1971`, merged to this fork's main as `1d66212c47` | Drop it when a pinned upstream release installs python-build-standalone interpreters in a workspace environment. |

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
  from the approved config-input and package/output-validation fix. `+dspot.8` adds patch 9; `+dspot.9` adds patch 10; `+dspot.10` adds patches 11 and 12. Every release from `+dspot.2` on is
  immutable: the launcher can't check the PEX's hash.
- When a patch's upstream PR is released, the next build drops it and bumps the `+dspot.N` label. When none is left,
  repositories go back to the plain official version and this branch is retired.
- Building:
  - use Pants' own release steps (`.github/workflows/release.yaml`: `release.py build-wheels`, then
    `package src/python/pants:pants-pex`) with `VERSION` set to the label above, on our own machines, never on
    GitHub-hosted runners. Every native file is linked against glibc 2.28 (the manylinux_2_28 floor), not in the
    manylinux container, which our runners refuse: `build-support/bin/dspot_release_build.sh`, run by
    `dspot-pants.yaml`'s build job, links them through zig's 2.28 stubs, and `dspot_glibc_floor.py` refuses the
    release when any native file of its wheel or PEX needs a newer glibc;
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
- This release commit changes only this record and `src/python/pants/VERSION`.
- `+dspot.10` is built by `.github/workflows/dspot-pants.yaml` on the pull request that adds this line: its `build` job runs
  the release steps above on our `dspot` runner and keeps the wheels and PEX as the run's `release-<head>` artifact,
  which is what gets published. Pull requests our worker lines open can start it since DSpotDevelopers/pants#28.
  #30's own run linked its natives against the runner's glibc 2.39 (`native_engine.so` named GLIBC_2.39), so its
  artifact was not published; the first run with the glibc 2.28 build is the one that is.

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
