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
persist credentials, and no repository or organization secrets are supplied to
those jobs. A skipped test job or successful packaging alone cannot report success.
The `DSpot Pants` status links to the run that built and tested its exact head.

Build and test steps run directly in the existing runner image. The build uses
`[self-hosted, linux, x64, dspot]`, and so do the focused tests (their suites need the build's CPU); API
bookkeeping uses `slot-cpus-1`. These jobs do not require Docker and have no job-level
`container` configuration. GitHub's built-in job container creates host binds
and performs a network prune that the fleet guard intentionally refuses.
The guard, runner images and fleet capacity are unchanged.

Both source jobs use the same pinned, fleet-cached setup-python action for
CPython 3.14 and select it through the upstream source bootstrap's `PY` setting.
The interpreter belongs to the runner tool cache; no manylinux-only path is used.
The checked source still drives the release build through `./pants`, rather than
substituting the runner's installed release for the candidate being tested.
The build installs its source-pinned Rust toolchain and Protoc as before, then runs
the checked source's `build-support/bin/dspot_release_build.sh`: it links every
native file against glibc 2.28 (the manylinux_2_28 floor) through zig, without a
container, and `build-support/bin/dspot_glibc_floor.py` fails the job when any
native file of the wheel or PEX needs a newer glibc. The script comes from the
pull request's head, so a change to how the release is built proves itself in its
own run; this workflow, like every `pull_request_target` definition, comes from
this default branch.

The artifacts remain unpublished CI outputs. Consumer qualification remains a
release-pin gate. Passing fork CI does not authorize publication.

The native engine is built once and handed to tests from the same source SHA.
Python selection is stock `--changed-since` with direct dependents. Rust's
JavaScript inference tests run only when their crate changes. Bash records CPU
and elapsed time; cgroup peak memory is recorded in each job summary when
available. Cold and warm timings must be read from actual runs before treating
the runner sizing as qualified.

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
