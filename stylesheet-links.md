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
- F1: not yet read line by line for comment style; the owner's review, or ours before he opens it

## What the owner's description needs: the facts, from the branch's own commits
(Upstream requires a human-written title and description: these are facts to write from, not text to paste. Some commit
bodies mention our fork's context; the squash commit takes the owner's description instead.)

### test(javascript): a stylesheet's @import and @source of a package infer the package (red)

A stylesheet links a workspace package with `@import "@flowsev/design"` or Tailwind's
`@source "@flowsev/ui"`, and a library's own stylesheet its siblings with
`@import "./tokens.css"`, but no rule reads a stylesheet, so a change to the package
reaches none of the apps that style themselves with it.

Six cells: a package `@import` (with a trailing modifier) and a Tailwind `@source`
infer the package's node target; `@source not` does not; a relative `@import`
infers the file's owner; a commented-out import and a URL infer nothing; an
unresolvable import is reported by the unowned-dependency setting; a file that is
not a stylesheet infers nothing. Red here: the request type does not exist.


### feat(javascript): a stylesheet's @import and @source infer what they link; 2.33.2+dspot.12

A stylesheet linked a workspace package (`@import "@flowsev/design"`, Tailwind's
`@source "@flowsev/ui"`) or a sibling (`@import "./tokens.css"`), but no rule read
it: a `file` or `resource` target infers nothing, and the JavaScript rules read
JavaScript and TypeScript only. So `--changed-dependents` could not reach an app
that styles itself with a changed design library.

`infer_stylesheet_dependencies` reads the `.css` source of a `file` or `resource`
target: a package specifier resolves through the same candidate map as a
JavaScript import of that package; a relative path resolves to the file's owner;
`@source not`, comments, URLs and absolute paths link nothing; an unresolved link
follows `[nodejs-infer].unowned_dependency_behavior`. Recorded as patch 13, with
its exit; the version label becomes 2.33.2+dspot.12.

Control: the six red cells pass, with the module's 45 others (51) and
package_json_test (14); ruff check and format are clean.


### test(javascript): a stylesheet resolves packages from its own folder (red)

Node resolves a stylesheet's imports from the file's folder, but the rule asked
for the package owning the target's address. A stylesheet owned by a target
declared above the app's package (dspot-company-data's cost-assistant
`library-tree`) could not reach the app's own third-party packages, and its
`@import "tailwindcss"` was reported unowned.

Control: test_a_stylesheet_resolves_packages_from_its_own_folder_whoever_owns_it.
Red here: nothing is inferred.


### fix(javascript): a stylesheet's links resolve from its own folder

The rule asked for the package owning the stylesheet's target address; Node
resolves a stylesheet's imports from the file's folder, so it now asks for the
package owning that folder.

Control: the red cell passes, with the other 51 inference cells and
package_json_test (66).


### test(javascript): a Tailwind @source of a package folder infers the package (red)

Tailwind's @source also takes a folder to scan (dspot-company-data's flowsev-atlas
and docx-template-builder use `@source "../../../../packages/ui"`); no file
owns a folder, so the link went unresolved.

Control: test_a_tailwind_source_of_a_package_folder_infers_the_package. Red
here: nothing is inferred.


### fix(javascript): a stylesheet link to a package's folder infers the package

A relative link no file owns is a folder; when that folder is a package's root
(Tailwind's `@source "../ui"`), the link infers that package's node target, as
`@source "@flowsev/ui"` does.

Control: the red cell passes, with the 52 other inference cells and
package_json_test (67).


### docs: release note for stylesheet link inference

## Evidence
- In our Pants build (dspot-company-data runs it daily); not run on upstream main here (no Rust toolchain on this host).
