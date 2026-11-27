# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""The tests job runs the change's selection within the qualified scope, with the tools upstream's
own test jobs install for it, so a qualified suite runs instead of skipping for a missing tool."""

from __future__ import annotations

from pathlib import Path

import yaml
from pants_release.generate_github_workflows import (
    PYTHON_VERSIONS_PER_PLATFORM,
    Platform,
    install_jdk,
)


def steps_of_the_tests_job() -> list[dict]:
    workflow = yaml.safe_load(Path(".github/workflows/dspot-pants.yaml").read_text())
    return workflow["jobs"]["tests"]["steps"]


def test_tests_job_installs_upstreams_jdk() -> None:
    assert install_jdk() in steps_of_the_tests_job()


def test_tests_job_runs_only_the_qualified_selection() -> None:
    (run,) = [s["run"] for s in steps_of_the_tests_job() if "./pants" in s.get("run", "")]
    select = 'dspot_qualified_selection.py "$BASE" > "$RUNNER_TEMP/qualified.txt"'
    assert select in run
    assert './pants --spec-files="$RUNNER_TEMP/qualified.txt" lint test' in run


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


def test_tests_job_restores_and_saves_its_pants_cache() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/dspot-pants.yaml").read_text())
    job = workflow["jobs"]["tests"]
    env = job["env"]
    # A restored LMDB must be owned by this job, never extracted onto a live host store.
    assert env["XDG_CACHE_HOME"] == "${{ github.workspace }}/.pants.d/qualification-cache"
    assert "XDG_CACHE_HOME" in env["PANTS_TEST_EXTRA_ENV_VARS"]
    assert "HERMETIC_ENV" in env["PANTS_TEST_EXTRA_ENV_VARS"]
    assert env["HERMETIC_ENV"] == "XDG_CACHE_HOME"
    assert env["PANTS_PANTSD"] == "false"

    steps = job["steps"]
    restore = next(
        i for i, s in enumerate(steps) if s.get("uses", "").startswith("actions/cache/restore@")
    )
    save = next(
        i for i, s in enumerate(steps) if s.get("uses", "").startswith("actions/cache/save@")
    )
    execute = next(i for i, s in enumerate(steps) if "./pants" in s.get("run", ""))
    assert restore < execute < save
    assert steps[restore]["with"]["path"] == ".pants.d/qualification-cache/pants"
    assert steps[save]["with"]["path"] == steps[restore]["with"]["path"]
    assert (
        steps[save]["with"]["key"] == "${{ steps.qualification-cache.outputs.cache-primary-key }}"
    )
    key = steps[restore]["with"]["key"]
    assert "${{ github.run_id }}" in key and "${{ github.run_attempt }}" in key
    assert steps[restore]["with"]["restore-keys"] in key
    # Keep work from a normally failed test pass, but do not snapshot a cancelled process.
    assert "!cancelled()" in steps[save]["if"]
    assert "success()" not in steps[save]["if"]
