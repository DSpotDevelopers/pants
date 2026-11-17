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

Repeat with `pull_request=8`, `9` and `10` after the reviewed bootstrap changes
are merged to `main` and the coordinator has enabled Actions and runner access.
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
