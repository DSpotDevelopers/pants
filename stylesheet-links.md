# stylesheet-links: facts for the owner's upstream PR

- **Branch:** DSpotDevelopers/pants `upstream-prep/stylesheet-links` at `681b2ea46`, on `upstream-prep/js-infer-ts-js-specifier`. Our patch: 13, stacked on the JS chain (patches 2-4).
- **Files:** `docs/notes/2.35.x.md`, `src/python/pants/backend/javascript/dependency_inference/rules.py`, `src/python/pants/backend/javascript/dependency_inference/rules_test.py`.
- **Tests:** `src/python/pants/backend/javascript/dependency_inference/rules_test.py`. Run: `pants test src/python/pants/backend/javascript/dependency_inference/rules_test.py`.
- **Release note:** in the branch, `docs/notes/2.35.x.md`, "#### Javascript".
- **Disclosure (upstream requires it):** the code and tests were written by an LLM agent (Claude, Claude Code) and reviewed on our fork by our review lines; the owner reviews and tests it before opening.
- **Notes:** Stacked: open after the JS chain lands, or rebase onto main then.

## Feedback applied
- F4
- F7
- F2: the new rule is called by name
- F1: every added comment read (27 Nov 18:50Z); they say why

## What the owner's description needs
(Facts to write from: upstream requires a human-written title and description.)
- **Problem:** JS dependency inference does not read stylesheets, so `@import "@scope/design"` or Tailwind's `@source "@scope/ui"` in a `.css` file infers nothing.
- **Change:** A stylesheet's `@import`/`@import url(...)` and Tailwind's `@source` links infer what they name: a package's node target, a file's owner, a package whose root folder a relative link names. Links resolve from the stylesheet's folder; `@source not` links nothing. It reads the `.css` sources of `file`/`resource` targets.
- **Tests:** Eight cases in `dependency_inference/rules_test.py`, among them resolution from the file's own folder and a Tailwind folder link.

## Evidence
- In our Pants build (dspot-company-data runs it daily); not run on upstream main here (no Rust toolchain on this host).
