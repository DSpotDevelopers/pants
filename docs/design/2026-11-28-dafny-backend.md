# Dafny verification and audit in DSpot Pants

Status: design for owner review; NO CODE AUTHORIZED.
Author: codex-d / developer-13. Task: TODO-737, within TODO-578.
Date: 28 November 2026. Revision: 2, exact section8 mapping.

## Decision requested

Approve a Dafny backend shipped inside DSpot's Pants distribution, enabled by
backend name in consumers. Stock `pants tailor` creates its file owners and one
`dafny_test` per workflow folder. That ordinary Pants test owns all three required
checks: verification without warnings, audit with zero findings, and comparison
of the locked specification files. Includes drive native changed-since selection.

Revision2 replaces the provisional mapping and the separate check/lint proposal.
It removes the proposed TOML project target and parser, which exceed R10.12's
boundary. It does not turn a check/lint success into a test result or retain a
second mandatory verification path. The owner's design approval is still required;
review approval and green documentation CI do not supply it.

## Exact requirements and traceability

Source: Dafny specification section8, as supplied verbatim by coordinator note
CODEX-D-737-R10-2811-1808, SHA prefix a13035409d7240da. These clauses replace
revision1's provisional associations; no claim is made to have read another version.

**R10.8:** Dafny support for Pants MUST live in our own Pants build (the one we
already patch), as a Dafny backend. The company repository stays stock Pants: its
configuration enables the backend by name, and nothing custom is inside it.

**R10.9:** Dafny files MUST be a known target kind. `pants tailor` writes a
`dafny_sources` target for a workflow's Dafny files and one `dafny_test` target per
workflow folder, its test entry (R10.3), with no BUILD file written by hand.

**R10.10:** The backend MUST read each Dafny file's `include` lines and infer its
dependencies from them, as Pants does for Python imports. A change to an included
shared file then selects every workflow that includes it. An include it cannot
resolve fails the target, naming the file and the line.

**R10.11:** The `dafny_test` target MUST run the workflow's checks as an ordinary
Pants test, so `pants test` and changed-since selection run it like any test:
`dafny verify` with no warnings, `dafny audit` with 0 findings, and the locked
spec files' comparison (R11.7, R11.8).

**R10.12, boundary:** This backend is the one named exception to the rule
"no custom Pants plugin". It covers Dafny files and their includes only. It is
offered upstream to Pants only if the owner decides so; no line does that on its own.

| Requirement | Design that meets it | Acceptance evidence required before release |
|---|---|---|
| R10.8 | Backend and all execution/inference rules ship in the fork; consumers enable its name | Installed fork runs an ordinary consumer fixture with no plugin, wrapper or custom runner in that fixture |
| R10.9 | Native source/generator/test target types; tailor emits source ownership and exactly one workflow test | Fresh tailor creates both; repeat tailor changes nothing; no duplicate entry ownership or handwritten BUILD |
| R10.10 | Include lexer, native ownership resolution and inferred transitive edges | Shared include edit selects every including workflow; missing include fails with including file and line |
| R10.11 | One native TestRequest returns the workflow's TestResult from verify, audit and spec-lock comparison | `pants test` and changed-since both execute all three gates; any warning, finding or lock mismatch fails |
| R10.12 | Dafny-only backend, with only the lock inputs R10.11 expressly requires | No TOML project parser, workflow/YAML parser, external repository plugin or generalized selector; upstream publication requires owner decision |

R10.3 supplies the canonical workflow test entry. R11.7/R11.8 supply the canonical
locked-file set, lock representation and approved-change rules. Their text is not
reproduced in the supplied note: this design references those contracts without
inventing another entry filename, lock format or approval mechanism. The build
implementation task must read and lock those details before its red specifications;
it must not substitute a convenience entry or checksum file for them.

## Targets and automatic ownership — R10.8, R10.9, R10.12

Proposed registration: `pants.backend.experimental.dafny`, implemented within
`src/python/pants/backend/dafny/` in this fork. The registration follows the existing
built-in backend pattern. The company enables that name in its Pants configuration;
there is no company `pants-plugins` package, executable shim or runner implementation.

| Target | Ownership | Role |
|---|---|---|
| `dafny_source` | One non-entry `.dfy` file | Generated file address and include dependency inference |
| `dafny_sources` | A workflow's ordinary Dafny sources | Native file target generator producing individual source addresses |
| `dafny_test` | The workflow's canonical R10.3 test entry and canonical lock sidecars | One ordinary test target per workflow folder, consuming its inferred Dafny closure and locked-spec inputs |

Stock `pants tailor` uses backend PutativeTargetsRequest rules. For each workflow
folder identified by the canonical R10.3 entry convention, it emits `dafny_sources`
and one `dafny_test`; it also handles included/shared Dafny libraries as source
owners. It obtains this from Dafny entry/source layout, not by reading WORKFLOW.yaml
or maintaining a workflow inventory. A newly discovered workflow with no valid
entry is diagnosed rather than represented by a passing empty test.

The entry belongs to `dafny_test`, so the generated `dafny_sources` excludes that
entry. Included ordinary files keep their individual source owners. Lock sidecars
belong to the test's canonical non-import inputs; lock-listed Dafny files retain
their existing source owners and become dependencies, never duplicate sources.
The backend shares include inference between source and test-entry fields.

No BUILD is written by hand. Repeated tailor is idempotent; a second entry or
ambiguous ownership is an error naming the folder and candidates. The design adds
no sibling all-to-all dependencies, per-file skip fields or manually maintained
include dependencies. Standard common fields, visibility and test options remain.

## Include inference and complete test inputs — R10.10, R10.11

1. Read Dafny's leading `include` directives with a lexer in the native backend,
   matching the pinned grammar: line comments, nested block comments, ordinary and
   verbatim strings, escaping and Unicode paths. A line regex is insufficient.
   Malformed include syntax fails, never returns an empty dependency list.
2. Resolve each include relative to its including file. Normalize internal `.`/`..`
   without allowing escape from the build root. Missing, unowned, ambiguous,
   unsupported or escaping paths fail the affected target. Diagnostics retain the
   including source path, line number, literal include and resolution reason.
3. Resolve file owners with Pants' InferDependenciesRequest. An `import M` inside
   the included program is a module reference, not a guessed filename convention.
   No unresolved include falls back to a directory/repository glob.
4. Traverse these inferred edges to capture every source in the test-entry closure.
   Cycles terminate in traversal; the real Dafny parser/typechecker judges program
   validity. A root that includes B which includes C has C in its process inputs.
5. Also capture the R11.7/R11.8 lock sidecars and complete locked Dafny specification
   set, even when a locked file is not reachable from the test entry. Those native
   comparison inputs must reach the test in selection and cache invalidation.
   They are the specific non-import inputs R10.11 requires, not a general new
   manifest-inference facility or exception list.

Verification names the canonical entry and uses `--verify-included-files`, so an
included body's failed proof is not hidden behind an assumed contract. Audit sees
the same complete program. A real-tool acceptance test must prove included-file
audit coverage; if the pinned auditor does not cover it from the entry, the native
rule names the closure files explicitly without introducing another graph.

Tool/runtime/solver files and all effective options are also declared process
inputs. The sandbox cannot read another host include through a symlink or ambient
HOME/config. The backend does not implement TOML project expansion, arbitrary
configuration discovery, code generation or translation of workflow YAML.

## Ordinary workflow test — R10.11

`dafny_test` implements TestFieldSet/TestRequest/TestResult in this fork. One batch
is one workflow, preserving ordinary address-level selection, output and failure
reporting. There is no separate mandatory `check` or `lint` invocation: neither is
a replacement for this test. The supported user/CI interface is:

```text
pants tailor path/to/workflows::
pants test path/to/workflows::
pants --changed-since=<BASE> --changed-dependents=transitive test
```

Each selected workflow test has three required stages:

1. **Spec-lock comparison:** compare every canonical locked file against the
   R11.7/R11.8 locked representation and approved revision. Missing locks, missing
   files, changed content, an invalid lock or a changed locked-file set fail the
   target. The comparison never rewrites a lock or accepts the current head as a
   newly approved specification merely because someone edited both files. The
   existing R11 approval contract supplies that authority; this test invents none.
2. **Verify:** execute the pinned `dafny verify` on the complete entry closure with
   warnings rejected. Exit0 with a warning is failure; a failed proof, parse/type
   error, timeout, cancellation or incomplete result is also failure. Use the
   pinned compiler's supported warning-failure option and validate it with an
   actual warning fixture; do not rely on warning text disappearing from stdout.
3. **Audit:** execute pinned `dafny audit`, require successful completion and
   exactly zero findings. Keep the raw audit report and diagnostics. A nonzero
   finding count fails even if the CLI exits0; an unreadable, missing, truncated
   or unrecognized result is failure, not a clean audit.

A failed input/lock admission may stop before expensive verification; an unrun
stage is never reported as passed. For valid admitted inputs, the result records
all three stage outcomes; verify and audit can report independent failures.
Only a complete success produces a passing workflow TestResult. Combine stage
products explicitly: they are not retry attempts, and the last process result
cannot overwrite an earlier failure. A failure in any workflow makes the ordinary
test goal nonzero. Reports identify workflow address,
entry, source locations, tool identity and the failed stage; retain stdout/stderr
and original reports through native TestResult output/extra_output/XML artifacts.
No shell wrapper translates results, and no new report service is proposed.

Dafny4.11's [audit command](https://github.com/dafny-lang/dafny/blob/v4.11.0/Source/DafnyDriver/Commands/AuditCommand.cs)
and [auditor](https://github.com/dafny-lang/dafny/blob/v4.11.0/Source/DafnyCore/Auditor/Auditor.cs)
resolve and report findings without necessarily failing the process. The backend
therefore validates the pinned completion/report protocol, including a uniquely
present nonnegative count, before constructing the TestResult. Real-tool tests
lock this protocol; source grep and `--compare-report` baselines do not replace it.

**Zero findings is R10.11's requirement, not an open policy option.** An intentional
extern finding still fails; this backend offers no trusted-door waiver, file-name
exemption or audit baseline. If a required contract cannot meet zero findings,
report the exact conflict to the owner; only a revised requirement can change the
gate. Revision1's suggestion to settle a separate exemption policy is withdrawn.

## Affected selection and Nx — R10.10, R10.11 plus owner condition

Pants selects changed owners and their transitive dependents, including workflow
tests. With workflows W1 and W2 including shared S, changing S selects both tests;
with A→B→C includes, a C edit reaches every workflow entry depending on A or B.
An independent W3 is untouched. Selection and cache inputs use the same graph.

A deleted still-included file fails inference with file/line. A lock or locked-spec
edit selects its owning workflow test. SCM errors fail selection. An empty valid
changed selection is distinct from a selected test with missing entry/lock input.
No parallel hand-written affected-file list or selection wrapper is proposed.

The owner's Nx condition applies before Dafny source enters Flowsev: native Nx
project admission must keep an independent Dafny-only change out of server/legacy
heavy lanes. The selected Dafny project's task delegates to ordinary `pants test`;
Pants supplies workflow/file precision. Native Nx graph edges must preserve any
cross-project shared-Dafny dependency before Pants selection is gated. Do not
intersect incomplete lists or widen to all Flowsev tests to hide missing edges.
Nx admission and its first master readback are a separate integration prerequisite,
not a new Nx plugin or selector implemented by this Dafny backend.

## Toolchain, sandbox and cache — implementation detail of R10.11

Use Pants ExternalTool/download/extract with a pinned version, platform, SHA256 and
archive length, capturing the bundled runtime and solver. Dafny4.11.0 is the proposed
initial version to match existing work; final pin is locked before red specs.
Unsupported platforms/versions or bad checksums fail. No ambient PATH executable,
repository Node/.NET install or live network access is a proof-process fallback.

Run sandboxed Pants Processes with stable relative paths and declared CPU/resource
limits through normal scheduling. There is no mutable shared solver/proof cache.
The native key covers the entry/closure and lock inputs, tool/solver digests,
platform, argv, effective options/environment, limits and backend semantic version.
A comparison input, included file or backend protocol change must invalidate its
stage and the aggregate workflow result. No second proof-specific cache is added.

Respect stock TestSubsystem cache scope, including force/per-session semantics,
for every process contributing to the test. Persistent verification reuse is for
successful processes; warning/finding interpretation and lock comparison still
apply on every cached result. A cached auditor exit0 with findings remains a failed
stage. Only all-three-stage success may be reused as aggregate success. Reports
must be available and labelled correctly on cache hits. No retry is introduced,
and a timeout/cancellation cannot be converted to success by cache reuse.

## Fork changes and exits — R10.8, R10.12

Inspected release base: `19168e5f24cd7d4c7a666d1daad9468e8b6cf677`.
Reserve implementation patch numbers only in that separate authorized build task;
this document changes no release pin or DSPOT-PATCHES entry.

| Proposed patch group | Required scope | Exit |
|---|---|---|
| Native Dafny targets and inference | Backend registration, source/test targets, tailor, include graph | Drop when a pinned upstream Pants supplies equivalent target ownership, automatic workflow tests and include selection, passing the acceptance matrix |
| Native Dafny test execution | Pinned tool, all three R10.11 stages, cache and standard test reports | Drop when that pinned backend supplies equivalent warning/audit/spec-lock gates; delete any redundant report adaptation as soon as the pinned tool offers the same contract directly |
| Consumer enablement, separate task | Backend-name setting, released Pants pin and tailor-generated BUILD files | Drop fork-specific pins when equivalent upstream support is pinned; normal generated BUILD ownership remains |

R10.12 is the named exception for this backend only. No core scheduler, test-goal
policy, SCM or cache change is proposed, and no generalized YAML/TOML parser,
translator, company plugin, baseline, new service or custom selector is included.
A discovered core defect needs its own approved general root fix; it cannot ride
this exception. Upstream submission occurs only if the owner decides, never by a
worker on its own.

## Acceptance specifications — requirement-linked, before implementation

These are future native Pants specifications, not tests added or run in this PR.
Owner design approval comes first; then the separate build task publishes reviewed
red executable specs, locks requirements and implements green bodies under SDD.

| Requirement | Required red/green evidence |
|---|---|
| R10.8 | Installed fork on a consumer fixture: only backend enablement and tailor output; no consumer plugin/runner; ordinary `pants test` works |
| R10.9 | Fresh workflow layout produces `dafny_sources` plus exactly one `dafny_test`; entry is owned once; repeat tailor unchanged; shared library ownership; missing/ambiguous entry fails; no handwritten BUILD |
| R10.10 | Lexer agrees with pinned grammar for comments/escapes/Unicode; relative/nested/cyclic includes; missing/unowned/escaping include fails with file and line; no sibling fan-out or guessed module filenames |
| R10.10/R10.11 | Actual SCM edit to a shared include selects every including workflow test; A→B→C transitively reaches all consumers; independent workflow untouched; deletion fails; unrelated edit schedules none |
| R10.11 verify | Clean proof passes; actual warning with exit0 cannot pass; parse/type error, false postcondition, bad included lemma, timeout and cancellation fail |
| R10.11 audit | Clean audit passes; actual exit0 with assume/axiom/verify-false/extern finding fails; included finding fails; missing/truncated/unrecognized report and nonzero exit fail |
| R10.11 locks, R11.7/R11.8 | Unchanged complete locked set passes; changed, added, removed or missing locked file/lock, invalid lock and unapproved replacement fail; comparison never writes or auto-accepts a lock |
| R10.11 result | All three stages required under one ordinary test address; any failed stage/workflow fails `pants test`; address, diagnostics and artifacts survive cache hits |
| R10.11 cache | Identical second input reuses eligible stage execution; include/entry/lock/options/tool/backend changes invalidate it; `--force` actually executes; cached warning/finding cannot become a pass |
| R10.12 | No non-Dafny parser/consumer plugin/selector; zero-finding gate has no exemption; no upstream action without owner decision |
| Owner Nx condition | Real Dafny-only PR/master changes run workflow tests without server heavy jobs; cross-project shared include reaches all consumers; selector failure blocks aggregate |

Use RuleRunner for native ownership/inference/rule results and this fork's existing
Pants integration harness for real CLI, SCM, cache and reports. Run Python controls
through stock Pants, never raw pytest/ruff. Unit stubs alone do not establish actual
Dafny warnings, include verification or audit exit semantics. No timeout increase,
proof retry or scope exception may turn these specs green.

## Owner decision and scope of this task

This task delivers the mapped design and answers the owner's questions. No owner
approval or questions were present in the PR discussion when revision2 was prepared.
The hold now waits on that decision, not missing R10 text or an audit exemption.
No code until the owner's yes; after his yes, implementation belongs to a separate
build task. Executable red-spec approval and Nx-before-source remain required.
Optional check/lint goals, TOML project support, workflow translation and broader
integration are beyond R10.8–R10.11 and are not part of this proposal.
Rollback: remove or revise this document; it has no runtime behavior to roll back.
