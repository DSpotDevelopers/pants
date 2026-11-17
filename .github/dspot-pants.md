# Checking the DSpot Pants fork

`dspot-pants.yaml` is a handwritten fork workflow, separate from the generated
upstream workflows. Its definition belongs on the fork's default branch, `main`.
It builds the requested source head; it never publishes a release or changes a pin.

Ready release PRs targeting `dspot/**` run through `pull_request_target` using
this trusted workflow. Only heads in DSpotDevelopers/pants may execute. The source
jobs have read-only credentials, and checkout does not persist them. Separate
light jobs record the result against the exact tested commit. Neither a skipped
test job nor a successful packaging step alone can produce a successful status.

To check an existing PR without changing its approved head, dispatch the workflow
from `main`, supplying its number:

```console
gh workflow run dspot-pants.yaml --repo DSpotDevelopers/pants --ref main -f pull_request=7
```

Repeat with `pull_request=8`, `9` and `10` after the workflow is reviewed,
merged to `main`, and admitted to the existing company runners.
The run resolves and records the current head and base before starting. The
`DSpot Pants` status links to the run that built and tested that head.

The build uses the company's existing `[self-hosted, linux, x64, dspot]` slots;
focused Python suites use `slot-medium`; API bookkeeping uses `slot-cpus-1`.
The native engine is built once and handed to tests from the same source SHA.
Python selection is stock `--changed-since` with direct dependents. Rust's
JavaScript inference tests run only when their crate changes. Bash records CPU
and elapsed time; cgroup peak memory is recorded in each job summary when
available. Cold and warm timings must be read from actual runs before treating
the runner sizing as qualified.

This is a fork-only CI change. The fork's default branch contains only
`dspot-pants.yaml`: upstream's scheduled, release, maintenance and test workflows
are removed along with the retired cherry-picker smoke test and its BUILD
bindings. The Pants patches and upstream release/generation tooling are retained.
Exit: upstream workflows return only if we ever push to upstream.

Actions stays off during review. The first merge cannot have a hosted check;
only the owner may approve that bootstrap exception. After that merge, the
coordinator enables Actions, admits the existing organization runner group and
confirms no GitHub-hosted job is queued. Then dispatch the four patch PRs; each
still requires approval and an actual green result on its exact head.

Rollback: disable Actions before reverting this PR, because reverting restores
upstream workflows with GitHub-hosted jobs. Existing statuses retain their tested
SHA. Do not regenerate upstream workflows on the fork's default branch.
