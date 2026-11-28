# Dafny verification and audit in DSpot Pants

Status: design for owner review; NO CODE AUTHORIZED.
Author: codex-d / developer-13. Task: TODO-737, within TODO-578.
Date: 28 November 2026. Revision: 1.

## Decision requested

Approve a Dafny backend shipped inside DSpot's Pants distribution. It uses the
existing `tailor`, dependency inference, `check` and `lint` interfaces. Repositories
consume it by enabling a backend from their pinned Pants build. They carry no
custom Pants plugin, proof runner, changed-file selector or audit baseline.

This document proposes the interface and acceptance tests. Approval of this prose
is not SPEC APPROVE of red executable specifications, implementation approval,
a release, a deployment, or permission to remove the Nx merge condition.

## Requirement source and the missing traceability input

The assignment CODEX-D-731-2811-1729, SHA prefix c61535d35bb1eae3, assigns
**R10.8, R10.9, R10.10 and R10.11** and states their combined outcome: Pants owns
Dafny verification and audit, selects affected work and needs no custom plugin
outside our Pants build. It also explicitly requires target types, inferred
file dependencies, caching, reporting, patch exits and proving tests.

The exact four numbered clauses were not included in that note. The published
[v8 specification](https://claude.ai/artifact/7phBie17rNXWJRXP1hZaT8) is linked by
the tracker, but its content could not be read here: the browser reader fails,
the public URL returns only a frame shell, and its content API returns HTTP403.
No plan issue was found; the Pants repository has issues disabled. A request for
the current clauses and issue link has been sent to the coordinator.

| Requirement | Authoritative text available here | Proposed coverage to reconcile before approval |
|---|---|---|
| R10.8 | Identifier and combined assignment only | Native targets and verification, sections below |
| R10.9 | Identifier and combined assignment only | Inference and affected selection, sections below |
| R10.10 | Identifier and combined assignment only | Audit gate, caching and reports, sections below |
| R10.11 | Identifier and combined assignment only | Distribution boundary, patch exits and acceptance matrix |

**Those associations are provisional, not quotations or a claim that these are
what each numbered requirement says.** Before implementation, replace this table
with the current plan's exact wording/version and check every clause. Any mismatch
changes this design for owner review before code. The following design is concrete
so the owner can assess it while that source is supplied.

The owner conditions carried by the note are read and retained: specification
first, reviewed red specifications before green code; Nx affected selection before
Dafny code enters Flowsev; and the five named Codex lines under the revised work
allocation. This document starts no additional builder or background service.

## Native targets and commands

Proposed registration: `pants.backend.experimental.dafny`, implemented within
`src/python/pants/backend/dafny/` in the Pants fork, following existing backend
registration conventions. Names below are proposed public API.

| Target | Owns | Meaning |
|---|---|---|
| `dafny_source` | Exactly one `.dfy` file | File ownership and inferred includes; participates in verify and audit |
| `dafny_sources` | Default `*.dfy` in one directory | Stock file target generator producing one `dafny_source` per file |
| `dafny_project` | One explicit Dafny TOML project file | Optional native Dafny project unit: owns its config and infers the members that the config names |

`dafny_sources()` is emitted by stock `pants tailor` for unowned files, using the
backend's normal PutativeTargetsRequest implementation. It is not a repository
BUILD generator script. Files get individual addresses; siblings do not acquire
all-to-all dependencies. Standard common fields, visibility and dependencies stay.
No per-file verify/audit bypass field is proposed.

`dafny_project` exists only where the author actually uses Dafny project semantics.
A project invocation checks its declared member set together; a broad project is
therefore honestly a broader unit. It is never synthesized for the whole repository
to make inference easier. The backend does not silently pick up IDE project files:
Dafny CLI project inputs are explicit. Switching between standalone/include mode
and project mode is an authored, visible compilation-unit choice.

Existing goals expose two separately named results:

- `pants check path/to/laws:: --only=dafny-verify`.
- `pants lint path/to/laws:: --only=dafny-audit`.
- A full qualification uses `pants check lint ::`; only Dafny-compatible field
  sets reach this backend. Selected Dafny files always get both gates in CI.

These are interface examples, not commands implemented or executed in this round.
No `test_shell_command`, generic shell target or repository runner stands in for
a language backend. `test` remains the owner of backend/unit/runtime tests; passing
those tests is not a substitute for the verifier and auditor results.

## Dependency inference and complete inputs

The graph comes from authored inputs, not from a hand-maintained dependency list.

1. Read a file's leading Dafny `include` directives with a small lexer in the native
   backend. Match the pinned language grammar, including nested block comments,
   line comments, ordinary/verbatim strings, escaping and Unicode paths. A regex
   over lines is insufficient. Parse failure is an error, never an empty dependency set.
2. Resolve each include relative to the including file, as Dafny does. Normalize
   `.` and internal `..` without allowing escape from the build root. Refuse absolute,
   missing, excluded or unowned inputs and ambiguous ownership, naming file/line
   and candidates. Symlinks cannot smuggle a file outside captured inputs.
3. Resolve paths with Pants ownership and InferDependenciesRequest. `import M`
   inside an already included program is a module reference, not an invented
   module-to-filename convention. There is no glob fallback for an unresolved import.
4. A project target reads its explicit TOML includes/excludes using Dafny's relative
   path rules; every matched member has one ordinary file owner. Invalid options,
   project references or unsupported syntax fail with a diagnostic. Config changes
   and member additions/deletions select the project; an empty unit cannot report
   that verification occurred. A project and a file entry that describe the same
   invocation are deduplicated by normalized process identity, not a second proof cache.
5. Hydrate the complete transitive closure into the process digest. Include cycles
   terminate through graph traversal; the real Dafny parser/typechecker decides
   whether the resulting program is valid. Tool/runtime files, effective options
   and every project/config input are captured too.

A standalone verification process names its selected root and uses
`--verify-included-files`: verification of a root alone must not merely assume
included bodies. Audit receives that same resolved program, including dependencies.
Tests must prove the pinned auditor covers included files; if it does not, audit
all closure files explicitly, deduplicating inputs before invocation. A successful
root result cannot hide a bad included file.

Explicit dependencies remain Pants' standard escape hatch for genuine non-import
runtime/code-generation data, not a routine way to spell a Dafny include. Generated
Dafny uses Pants' existing codegen request interface when its producer exists:
workflow YAML and translator/templates must be actual producer dependencies.
This backend does not add the old per-workflow model generator or invent the
translator assigned to another line. Missing generated-source ownership blocks
that integration rather than checking a stale checked-in copy.

## Affected selection and the Nx boundary

Pants computes affected file owners plus **transitive** dependents. Direct-only
selection is insufficient: if A includes B and B includes C, editing C must check
A as well as B and C. A project member/config change must reach its project root.
Selection and cache invalidation use this same graph, not separate file lists.

Proposed CI invocations use the admitted immutable BASE/HEAD range:

```text
pants --changed-since=<BASE> --changed-dependents=transitive check --only=dafny-verify
pants --changed-since=<BASE> --changed-dependents=transitive lint --only=dafny-audit
```

An unrelated edit schedules no Dafny process. A law/include edit schedules only
its real dependent proof units. Deleting a still-included file fails inference;
it does not disappear from a successful check. SCM errors fail the invocation.
An empty valid changed selection is distinct from an empty/failed proof program.

Nx remains Flowsev's native project-selection boundary (TODO-715/#13937): a
Dafny-only independent package change must not admit server/legacy heavy lanes.
The selected Dafny project delegates its real checks to these Pants goals after
this backend is released; the current empty-package assertion is not retained as
a proof result once source exists. Pants owns file precision within that project.
The integration must preserve real cross-project dependency edges so an outside
include/translator change cannot be filtered out by Nx before Pants sees it.
Do not intersect two incomplete path lists. If that edge cannot yet be represented,
block the integration and repair the native graph; do not widen to all Flowsev tests.
The first merged master Dafny-only readback is required before admitting source.

## Toolchain, sandbox and cache

Use Pants' ExternalTool/download/extract machinery with a version, platform,
SHA256 and archive length for each admitted platform. Proposed first toolchain is
Dafny4.11.0 to match the existing work; the owner must confirm it against the plan.
Capture its bundled runtime and solver. Unknown versions/platforms or checksum
mismatch fail before verification. A workstation PATH executable is not a fallback.

Run ordinary sandboxed Pants Processes. No repository Node/.NET install, host HOME,
shared mutable solver cache, ambient project discovery or live network call enters
a proof. Keep source-relative paths stable and pass the configured CPU request to
Pants' normal scheduling/resource mechanism. Use explicit verifier resource limits;
a timeout, cancellation or tool failure is never proof success.

The Pants process key covers the root/member set, complete input digest, toolchain
and solver digest, platform, argv, relevant environment, resource options, project
options, generated inputs and backend cache generation/version. Verify and audit
have different command identities. A toolchain/parser/report-adapter semantic
change invalidates prior results through an explicit backend cache version when
input/argv changes alone would not change the key. No proof-specific cache service.

Use `ProcessCacheScope.SUCCESSFUL` for verification: failed/incomplete verification
is not a persistent green artifact. The native process cache can reuse an auditor
process that exits0 with findings; the backend must still interpret its captured
report as failed every time. A cache hit saves execution, never waives policy.
Pants' CheckResults/LintResults still render on a cache hit, and cached output
reports are materialized by the existing report writer. CI's normal remote-cache
trust boundary also applies to proof results; no stronger certificate is claimed.

## Verification, audit and reporting

Each unit reports its Pants address/root, tool version and ordinary diagnostics.
`dafny verify` exit0 is required; malformed syntax, failed proof, resource exhaustion
or nonzero exit produces a nonzero CheckResult. Emit the verifier's declared report
and stdout/stderr through stock CheckResult.report, under the normal dist/check
report tree. Exact supported report switches are locked by real-tool tests before
implementation approval, not invented in a shell wrapper.

The auditor is a separate `LintTargetsRequest`/LintResult implementation. In
[Dafny4.11's command](https://github.com/dafny-lang/dafny/blob/v4.11.0/Source/DafnyDriver/Commands/AuditCommand.cs),
audit resolves rather than verifies. Its
[auditor](https://github.com/dafny-lang/dafny/blob/v4.11.0/Source/DafnyCore/Auditor/Auditor.cs)
reports a finding count and writes text/Markdown/HTML; findings need not make the
process fail. **Exit0 by itself cannot pass the audit gate.**

Proposed initial policy is zero findings in the audited specification closure.
The native backend requests a fixed pinned report format, validates completion
and a uniquely present nonnegative count, and returns nonzero LintResult for any
finding. A missing/truncated/unrecognized report or count is a tool/protocol failure,
not a clean audit. Keep the original report, stdout and stderr as stock lint reports;
attach diagnostics to the source location. Do not grep source text for `assume`
and pretend that is the auditor. Do not use `--compare-report` to grandfather findings.

Intentional externally implemented contracts also need an explicit owner decision:
strict zero findings may reject the plan's trusted door contracts. This design does
not silently waive them, add an allow-list, or call an extern body proven. Before
implementation, reconcile R10's audit policy with the plan's two-door contracts.
If a structural trusted-boundary policy is required, define it in the reviewed red
specification and keep those findings visible; no file-name exemption or baseline.
Unknown findings always fail. This is an approval question, not permission to skip audit.

## Fork changes and their exits

Inspected maintained release base: `19168e5f24cd7d4c7a666d1daad9468e8b6cf677`.
This design changes none of its code or release pins. Future work is ordinary
reviewed patches on that repository's release line, with red specs approved first.
Reserve patch numbers only when implementation is authorized; existing numbers
are already occupied in DSPOT-PATCHES.md.

| Proposed patch group | Location and purpose | Exit, with a measurable replacement test |
|---|---|---|
| Native Dafny language support | Built-in backend registration, targets, tailor, include/project inference, toolchain and check integration | Drop the fork delta when a pinned upstream Pants provides equivalent ownership/inference/verification and passes the acceptance matrix below |
| Native audit integration | Built-in lint adapter, strict completion/finding policy and ordinary reports | Drop when that pinned backend supplies the same fail-closed audit policy/report contract; if Dafny gains a suitable exit/report interface, delete the redundant count adaptation immediately |
| Consumer enablement | Repository backend setting and normal BUILD ownership after the released fork is pinned | Remove temporary release pins/config deltas when the equivalent upstream build is pinned; BUILD targets remain normal language ownership |

No core scheduler/cache/SCM change is proposed. If a real stock interface defect is
found, bring a separately reproduced general fix with its own exit; never special
case Dafny in `changed`, the test goal or an external repository plugin.
Upstream submission is optional and belongs to the owner, as DSPOT-PATCHES.md says.

## Acceptance specifications before implementation

All rows become native Pants tests in this fork. First publish the failing specs,
get independent SPEC APPROVE and owner design approval, then lock requirements
and implement their green bodies. No tests are implemented or claimed passing here.

| Area | Required red/green evidence |
|---|---|
| Ownership/tailor | New `.dfy` files get one generated owner; repeated tailor is unchanged; multiple owners/empty selected program refuse |
| Include lexer | Comments, nested comments, strings, escapes, verbatim/Unicode paths, repeated includes and non-directive text agree with pinned Dafny grammar; malformed syntax never returns no dependencies |
| Inference | Relative/nested includes, cycles, ambiguity, missing/escaping/symlinked files; import names are not guessed filenames; no sibling fan-out |
| Projects | Exact glob membership, excludes, config edits, added/deleted members, unsupported config; standalone vs explicit project semantics match real CLI behavior |
| Complete proofs | Root passes but included lemma fails; root parse/type error; false postcondition; unchanged correct root; included audit finding is visible and blocking |
| Audit gate | Native auditor exit0 with assume/axiom/verify-false findings still fails lint; clean audit passes; malformed/missing report, nonzero exit and cancellation fail; trusted-door policy has its own owner-approved negative/positive cases |
| Selection | A→B→C edit checks A/B/C; independent D untouched; deleted C fails A/B; unrelated edit schedules none; config/tool/translator edits reach all actual consumers |
| Cache | Instrument real child executions: identical second input reuses successful results and reports; root/include/options/tool/backend-version changes execute again; failed verification cannot become a warm-cache pass |
| Isolation | Fresh sandbox and warm cache yield the same result; no undeclared host include/tool read, network fallback or mutable shared-state dependence |
| Reporting | Verify and audit have separate names/exit results, root addresses and retained diagnostics/reports, including on cache hits; one failed unit fails the goal |
| Nx integration | Actual Dafny-only PR and master changes run real Dafny gates with no server/legacy heavy jobs; cross-project include/translator edit selects every consumer; selector/tool failure blocks the aggregate |

Use RuleRunner for target/inference/rule results and this fork's native Pants
integration harness for real CLI, SCM, caching and reports. Run them with stock
`pants test`/`lint`/`check`; never raw Python test/lint tools. Unit stubs alone do
not prove the pinned tool's include, exit-code or report behavior. Do not extend
CI deadlines, retry failed proofs or add an exception to make these cells pass.

## Owner review and implementation gate

The owner can accept/reject this concrete design in this PR. Before any code:

1. Supply the current R10.8–R10.11 clauses/version and reconcile the provisional
   traceability table; confirm toolchain and trusted-door audit policy.
2. Confirm the native goals/target API, sandbox/cache contract and fork exits.
3. Review and approve the red executable specifications under the locked requirements.
4. Prove and land the Nx admission prerequisite before source enters Flowsev.

Then implement one reviewed part at a time, qualify the fork, publish through its
normal release path, pin it in consumers and replace empty-stage checks with real
Pants gates. No implementation, dependency install, service change or deployment
is performed by this document. Rollback of the design is removal of the document;
there is no runtime behavior to roll back.
