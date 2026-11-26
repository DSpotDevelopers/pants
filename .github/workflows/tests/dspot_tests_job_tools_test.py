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
