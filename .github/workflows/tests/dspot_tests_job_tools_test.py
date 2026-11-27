# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""The tests job runs the change's selection within the qualified scope, with the interpreters
upstream's own test jobs install for it, so a qualified suite runs instead of skipping for want of
one."""

from __future__ import annotations

from pathlib import Path

import yaml
from pants_release.generate_github_workflows import (
    PYTHON_VERSIONS_PER_PLATFORM,
    Platform,
)


def steps_of_the_tests_job() -> list[dict]:
    workflow = yaml.safe_load(Path(".github/workflows/dspot-pants.yaml").read_text())
    return workflow["jobs"]["tests"]["steps"]


def test_tests_job_runs_only_the_qualified_selection() -> None:
    (run,) = [s["run"] for s in steps_of_the_tests_job() if "./pants" in s.get("run", "")]
    # the cells outside the contract come out as pytest args Pants appends to the configured ones
    outside = '"$RUNNER_TEMP/outside-the-contract.txt"'
    select = f'dspot_qualified_selection.py "$BASE" {outside} > "$RUNNER_TEMP/qualified.txt"'
    assert select in run
    pants = './pants --spec-files="$RUNNER_TEMP/qualified.txt"'
    assert f'{pants} --pytest-args="@$RUNNER_TEMP/outside-the-contract.txt" lint test' in run


def test_tests_job_installs_upstreams_test_interpreters() -> None:
    setup = [
        s for s in steps_of_the_tests_job() if s.get("uses", "").startswith("actions/setup-python@")
    ]
    assert len(setup) == 1
    installed = set(setup[0]["with"]["python-version"].split())
    # 3.14 is the pinned standalone interpreter the bootstrap step puts on PATH. setup-python
    # publishes no 3.7 for the runners' Ubuntu 24.04.
    assert set(PYTHON_VERSIONS_PER_PLATFORM[Platform.LINUX_X86_64]) - {"3.7", "3.14"} <= installed


def test_tests_job_runs_pants_at_the_slots_cpus() -> None:
    # Pants runs one process per CPU it sees, and a runner's container sees the host's CPUs: the job
    # sets it from the slot's granted CPUs before Pants runs, never a fixed number in its env.
    workflow = yaml.safe_load(Path(".github/workflows/dspot-pants.yaml").read_text())
    assert "PANTS_PROCESS_EXECUTION_LOCAL_PARALLELISM" not in workflow["jobs"]["tests"]["env"]
    runs = [s.get("run", "") for s in workflow["jobs"]["tests"]["steps"]]
    budget = next(i for i, r in enumerate(runs) if "build-support/bin/dspot_slot_cpus.py" in r)
    assert "PANTS_PROCESS_EXECUTION_LOCAL_PARALLELISM=" in runs[budget]
    assert budget < next(i for i, r in enumerate(runs) if "./pants" in r)
