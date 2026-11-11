# DSpot's Pants build

This is official Pants **2.33.2** plus only the patches below. Every patch is open upstream and has an exit.
Apart from the version label and this file, nothing else differs from the `release_2.33.2` tag.

Version: `2.33.2+dspot.2`. A repository pins it like any Pants version: `pants_version = "2.33.2+dspot.2"` in
`pants.toml`. The stock scie-pants launcher fetches it through `PANTS_BOOTSTRAP_URLS`, set in the repository's
committed `.pants.bootstrap`. There's no wrapper script.

| # | Patch (commits on this branch) | Upstream | Exit |
|---|---|---|---|
| 1 | Install the transitive dependencies of pnpm workspace packages (its test and fix commits; the PR's 2.34 docs commit is left out) | pantsbuild/pants#23754, open | Drop it when a Pants release we pin contains #23754. |
| 2 | JS inference finds the owner of an imported non-module file, such as `./x.css` or `./rows.json` | Not opened yet; the fix's branch for upstream is `dspot/js-infer-non-js-files` on this fork | Drop it when a Pants release we pin contains the upstream fix. |

## Rules for this branch

- Patches come only from open upstream PRs, each with its row above. A patch that upstream rejects is either reworked
  upstream or removed; it is never kept as a local-only change.
- `+dspot.2` is the same source as `+dspot.1`, rebuilt with only the version label changed, so it can be published as an
  immutable release (immutable releases were enabled on this fork after `+dspot.1` was published).
- When a patch's upstream PR is released, the next build drops it and bumps the `+dspot.N` label. When none is left,
  repositories go back to the plain official version and this branch is retired.
- Building:
  - use Pants' own release workflow (`.github/workflows/release.yaml`: `release.py build-wheels`, then
    `package src/python/pants:pants-pex`) in the same manylinux_2_28 container, with `VERSION` set to the label above;
  - the artifacts' names follow the official ones, `pants.<version>-cp314-<platform>.pex`.
