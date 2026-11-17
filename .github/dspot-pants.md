# Checking the DSpot Pants fork

`dspot-pants.yaml` is a handwritten fork workflow, separate from the generated
upstream workflows. Its definition belongs on the fork's default branch, `main`.
It builds the requested source head; it never publishes a release or changes a pin.

Ready PRs, including stacked PRs targeting another change branch, run through
`pull_request_target` using the trusted default-branch workflow. Every job requires an author association
of OWNER, MEMBER or COLLABORATOR and a head in DSpotDevelopers/pants. A fork head
is refused even when its author has one of those associations. Missing PR metadata
fails closed before a runner is assigned. The source job rechecks the current PR
association before recording a pending status.

There is no `pull_request` or manual-dispatch entry point: the former allows the
PR to change its workflow definition, and the latter has no PR author association.
After this change reaches the default branch, synchronize or reopen an eligible
PR to request a run. A rerun of an older run uses its older workflow definition;
it does not prove this guard. Existing queued pre-guard runs likewise keep their
original definition and need separate coordinator disposition.

Only the source and result jobs can write commit statuses, and neither checks out
PR code. The build and test jobs have only read permission; checkout does not
persist credentials, and neither receives repository or organization secrets.
Consumer qualification uses a company-read credential only in the trusted
snapshot API action and its checkout action, never in a command or PR-head checkout. A skipped test or consumer job,
or successful packaging alone, cannot report success.
The `DSpot Pants` status links to the run that built and tested its exact head.

The build uses the company's existing `[self-hosted, linux, x64, dspot]` slots;
focused Python suites use `slot-medium`; API bookkeeping uses `slot-cpus-1`.
The native engine is built once and handed to tests from the same source SHA.
Python selection is stock `--changed-since` with direct dependents. Rust's
JavaScript inference tests run only when their crate changes. Bash records CPU
and elapsed time; cgroup peak memory is recorded in each job summary when
available. Cold and warm timings must be read from actual runs before treating
the runner sizing as qualified.

The consumer matrix downloads the `release-<head>` artifact from the same run;
it never launches the company's pinned Pants or downloads a substitute release.
It checks the artifact's version against the source build's version, then uses
that executable for stock `tailor`, `filedeps --transitive`, `check` and `test`.
The four consumers are `packages/design`, `packages/plugin-sdk`, `packages/store`
and `workflows/accountancy-library/core`. Every concrete exported file must occur
in its own manifest's transitive file dependencies before that package's tests
can qualify. A missing export, test failure, missing executable, private-checkout
failure or skipped matrix member prevents the exact-head status from turning green.

The private checkout requires the fork repository secret `COMPANY_READ_TOKEN`,
with **Contents: read** access to `DSpotDevelopers/dspot-company-data` only, managed
and rotated by the runtime owner. It must not grant writes. One light metadata
job resolves company `main` once; every matrix member checks out that same
immutable commit. Each records the company commit with the candidate source SHA
and consumer in the run summary, and never persists the credential. No company files are
uploaded as public artifacts; the private checkout and downloaded candidate are
removed at job end. Consumer qualification uses the existing
`slot-medium` runners, one test process per job, and reports elapsed/CPU time and
cgroup peak memory. Its live runtime and memory qualification remain unproven
until the first complete run; no new runner or capacity is requested.

The default-branch workflow must contain this change before new runs qualify.
Existing runs retain their old definitions and cannot prove consumer qualification.
Passing this check qualifies only the recorded source and company commits; it does
not publish a release, change a pin, or qualify a different source combination.
The release-pin proposal waits for this required check to pass with the combined
reviewed release source, then references that build's immutable published artifacts.

This is a fork-only CI change. Exit: upstream workflows return only if we ever
push to upstream. The Pants patches and upstream release/generation tooling stay.

The bootstrap retirement has three parts: scheduled and generated workflows,
manual release assistants, and the cherry-picker with its CI-only smoke test and
BUILD bindings. Actions must stay off until all three are merged and the default
branch contains only `dspot-pants.yaml`. Do not regenerate upstream workflows on
the fork's default branch.

Only the owner may permit the first checkless bootstrap merge. After the complete
reviewed retirement, the coordinator enables Actions, admits the existing runner
group and confirms no GitHub-hosted job is queued. Each patch PR still requires
approval and an actual green result on its exact head.

Rollback: switch Actions off before reverting any retirement, because reverting
restores upstream jobs. Existing statuses retain their tested SHA.
