# js-infer-non-js-files: facts for the owner's upstream PR

- **Branch:** DSpotDevelopers/pants `upstream-prep/js-infer-non-js-files` at `6e759ecba`, on pantsbuild/pants main 83e5bf9f0. Our patch 2 (non-module imports) (DSPOT-PATCHES.md).
- **Files:** `src/python/pants/backend/javascript/dependency_inference/rules.py`, its `rules_test.py`, `docs/notes/2.35.x.md`.

## What the owner's description needs
- **Problem:** imported non-module files (`./index.css`, `./rows.json`) are only tried with a JS/TS extension appended, so they are always unowned.
- **Change:** The exact path is a candidate too, so the target owning that file (`resources`, `files`) becomes a dependency; extension-completed candidates stay for module paths with dots (`./moduleA.generated`).
- **Tests:** 81 lines in `rules_test.py`: a CSS and a JSON import inferred from their owners; the dotted module path still completed. Run: `pants test src/python/pants/backend/javascript/dependency_inference/rules_test.py`.
- **Release note:** in the branch, `docs/notes/2.35.x.md`, "#### Javascript".
- **Disclosure (upstream requires it):** the code and tests were written by an LLM agent (Claude, Claude Code), reviewed on our fork by our review lines; the owner reviewed and tested it before opening.

## Feedback applied
- F4: the note moved from `2.34.x.md` (where our fork's branch had it) to `2.35.x.md`, the version upstream main develops, worded as a fix of unowned imports.
- F1: the new comments say why (TypeScript's substitution, why the exact path is a candidate), never what the line does.
- F7: the facts above, for the owner's own words; no text here is to be pasted.

## Evidence
- In our Pants build since `2.33.2+dspot.3/.4`, used by dspot-company-data's whole scope daily.
- Not run on upstream main here (no Rust toolchain on this host); the code is byte-identical to the fork branch, and upstream changed nothing in these files since its base (94f4527b0 -> 83e5bf9f0).
