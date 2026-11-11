# DSpot's Pants build

This is official Pants **2.33.2** plus only the patches below. Every patch goes upstream and has an exit.
Apart from the version label and this file, nothing else differs from the `release_2.33.2` tag.

Version: `2.33.2+dspot.4`. A repository pins it like any Pants version: `pants_version = "2.33.2+dspot.4"` in
`pants.toml`. The stock scie-pants launcher fetches it through `PANTS_BOOTSTRAP_URLS`, set in the repository's
committed `.pants.bootstrap`. There's no wrapper script.

| # | Patch (commits on this branch) | Upstream | Exit |
|---|---|---|---|
| 1 | Install the transitive dependencies of pnpm workspace packages (its test and fix commits; the PR's 2.34 docs commit is left out) | pantsbuild/pants#23754, open | Drop it when a Pants release we pin contains #23754. |
| 2 | JS inference finds the owner of an imported non-module file, such as `./x.css` or `./rows.json` | Branch `dspot/js-infer-non-js-files` on this fork, on Pants main; the issue and PR are posted by a person (Pants requires human-written text) | Drop it when a Pants release we pin contains the upstream fix. |
| 3 | JS inference reads a bundler query's file: `./App.tsx?raw`, `./logo.svg?url` | Branch `dspot/js-infer-bundler-query` (on patch 2's), posted the same way | Drop it when a Pants release we pin contains the upstream fix. |
| 4 | A TypeScript `.js` specifier infers the source it compiles from: `./errors.js` -> `errors.ts`/`.tsx`/`.d.ts`, `./View.jsx` -> `View.tsx` | Branch `dspot/js-infer-ts-js-specifier` (on patch 3's), posted the same way | Drop it when a Pants release we pin contains the upstream fix. |
| 5 | TypeScript check keeps the discovered named/root Node project and a sandbox-relative wrapper path (`9b4d1aed7`, `cfe58a301`) | Branch `dspot/ts-check-named-root-project` on this fork, on Pants main (60df85631); the issue and PR are posted by a person, as for patches 2-4 | Drop it when a Pants release we pin contains the equivalent named-project/root-wrapper fix. |
| 6 (next build) | Preserve TypeScript compiler inputs: imported JavaScript, exported declarations, JSON resources and module-specific declarations | Internal branch `codex-r/typescript-input-closure`; coordinator/owner owns external review and submission | Drop it when a Pants release we pin contains equivalent compiler-input and export-inference fixes. |
| 7 (next build) | TypeScript check builds the configs owning the selected sources, with their declared project references, rather than every member of a Node resolve | Internal branch `codex-r/typescript-input-closure`; coordinator/owner owns external review and submission | Drop it when a Pants release we pin separates TypeScript programs from Node resolves. |

## Rules for this branch

- Patches come only from fixes that go upstream, each with its row above. A patch that upstream rejects is either reworked
  upstream or removed; it is never kept as a local-only change.
- `+dspot.2` is the same source as `+dspot.1`, rebuilt with only the version label changed, so it can be published as an
  immutable release (immutable releases were enabled on this fork after `+dspot.1` was published). `+dspot.3` adds
  patches 3 and 4; `+dspot.4` adds patch 5. Every release from `+dspot.2` on is immutable: the launcher can't check the PEX's hash.
- When a patch's upstream PR is released, the next build drops it and bumps the `+dspot.N` label. When none is left,
  repositories go back to the plain official version and this branch is retired.
- Building:
  - use Pants' own release steps (`.github/workflows/release.yaml`: `release.py build-wheels`, then
    `package src/python/pants:pants-pex`) with `VERSION` set to the label above, on our own machines, never on
    GitHub-hosted runners. So far the builds ran against a glibc 2.28 sysroot (the manylinux_2_28 floor), not the
    manylinux container, and every native file's highest symbol was checked to be GLIBC_2.28;
  - the artifacts' names follow the official ones, `pants.<version>-cp314-<platform>.pex`.
