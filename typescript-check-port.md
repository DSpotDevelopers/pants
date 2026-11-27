# TypeScript check, patches 5-8: three upstream drafts (files only; no branch yet)

Decision (27 Nov 18:43Z): the port goes after the owner's deadline. These are the facts for three PRs, in upstream's order of review. Each is opened only by the owner, and each needs its branch ported and `check_test.py` run on upstream main first.

**Why three:**
- the contribution guide asks to split big changes;
- tobni asked on #22461 for check to follow the command line's selection (draft 2 is that);
- our fork's 23 commits interleave the three concerns.

**Upstream changes to merge with first (main 83e5bf9f0):**
- 029bd904d (#23343, buf) hydrates `SourcesField` with `for_sources_types=(JSRuntimeSourceField,)` and `enable_codegen=True`, where ours hydrated every source of the project's targets;
- 5e090d08d (#23505) uses `find_sh`.

The merged hydration must keep upstream's codegen and our assets. Only check_test on main can settle it.

## Draft 1: the repository-root Node project (our patch 5)
- **Problem:** with the TypeScript project at the repository root, check's resolve lookup (empty path) and its wrapper path (leading slash) do not work, so `pants check` fails before type-checking.
- **Change:** the root project keeps its discovered resolve and a sandbox-relative wrapper path. Subfolder projects keep stock lookup and unnamed `package_json()` targets.
- **Tests:** the root-project cases of our `check_test.py` (named root packages: success and type-error exits).
- **Feedback:** F1, F4 (a fix note in 2.35.x.md, "#### TypeScript"), F7.

## Draft 2: check the configs that own the selected sources (our patches 6 and 7)
- **Problem:** `pants check` on some TypeScript files builds every program of the Node resolve. It is slow, and errors of unselected programs fail the selected ones. Imported JavaScript (an `allowJs` program's inputs) is missing from the compiler's inputs.
- **Change:**
  - check builds the tsconfigs that own the selected sources, with their declared project references;
  - the compiler's inputs include imported JavaScript;
  - config discovery inventories the project's sources and configs, never the installed resolve's links (pnpm workspace links form cycles).
- **Tests:** `check_selection_test.py` (selection, siblings, references) and `check_inputs_test.py` (imported JavaScript, unrelated assets left out).
- **Feedback:**
  - F3 is tobni's own ask (#22461: "typecheck based on arguments, not whole projects");
  - F2 (call-by-name), F1, F4, F7;
  - `OrderedSet` where order matters (#22461).
- **Note:** upstream's 2.34 branch hydrates transitive dependencies (029bd904d), but not a pnpm workspace package's own JS and declaration sources for its importers. On our repository that still gave 98 TS2305 errors, which is why patch 6 stayed.

## Draft 3: generated and packaged config data (our patch 8)
- **Problem:** a tsconfig's generated inputs (codegen) and packaged data are not given to the compiler. A package-shell target is built through source codegen instead of `package`.
- **Change:**
  - check consumes the generated and packaged dependencies of its active tsconfigs;
  - a package-shell target builds through `package`;
  - output validation matches captured names without walking dependency links.
- **Tests:** the generated/package diagnostic cases of our `check_inputs_test.py`.
- **Feedback:** F1, F4, F7. This draft has to be reconciled with 029bd904d's codegen hydration first.
