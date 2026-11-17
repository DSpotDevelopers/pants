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

Repeat with `pull_request=8` after the workflow itself is reviewed and green.
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

Repository Actions must be enabled and the existing organization runner group
must admit this fork. Keep the inherited upstream workflows disabled in the fork:
their external runner labels and publishing/audit jobs are not this pipeline.
Rollback is reverting this workflow; existing statuses retain their tested SHA.
