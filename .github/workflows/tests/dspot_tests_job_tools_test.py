# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""The tests job installs the tools upstream's own test jobs install, so a selected backend suite
runs instead of skipping for a missing compiler or interpreter."""

from __future__ import annotations

from pathlib import Path

import yaml
from pants_release.generate_github_workflows import (
    PYTHON_VERSIONS_PER_PLATFORM,
    Platform,
    download_apache_thrift,
    install_go,
    install_jdk,
)


def steps_of_the_tests_job() -> list[dict]:
    workflow = yaml.safe_load(Path(".github/workflows/dspot-pants.yaml").read_text())
    return workflow["jobs"]["tests"]["steps"]


def test_tests_job_installs_upstreams_jdk_go_and_thrift() -> None:
    steps = steps_of_the_tests_job()
    for step in (install_jdk(), *install_go(), download_apache_thrift()):
        assert step in steps, step["name"]


def test_tests_job_installs_upstreams_test_interpreters() -> None:
    setup = [
        s for s in steps_of_the_tests_job() if s.get("uses", "").startswith("actions/setup-python@")
    ]
    assert len(setup) == 1
    installed = set(setup[0]["with"]["python-version"].split())
    # 3.14 is the pinned standalone interpreter the bootstrap step puts on PATH. setup-python
    # publishes no 3.7 for the runners' Ubuntu 24.04.
    assert set(PYTHON_VERSIONS_PER_PLATFORM[Platform.LINUX_X86_64]) - {"3.7", "3.14"} <= installed
