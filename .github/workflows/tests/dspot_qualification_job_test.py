# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""Qualification must provide the tools its selected integration suites actually use."""

from pathlib import Path

import yaml


def _tests_job() -> dict:
    return yaml.safe_load(Path(".github/workflows/dspot-pants.yaml").read_text())["jobs"]["tests"]


def test_python_313_integration_cells_have_their_interpreter() -> None:
    (setup,) = [
        step
        for step in _tests_job()["steps"]
        if step.get("uses", "").startswith("actions/setup-python@")
    ]
    versions = {
        ".".join(version.split(".")[:2])
        for version in setup["with"]["python-version"].split()
    }
    assert "3.13" in versions


def test_core_docker_integration_cells_get_a_guarded_socket() -> None:
    assert "docker-socket" in _tests_job()["runs-on"]


def test_changed_targets_use_the_release_lines_qualified_selection() -> None:
    commands = "\n".join(step.get("run", "") for step in _tests_job()["steps"])
    assert '"$PY" build-support/bin/dspot_qualified_selection.py "$BASE"' in commands
    assert './pants --spec-files="$RUNNER_TEMP/qualified.txt" lint test' in commands
    assert './pants --changed-since="$BASE" --changed-dependents=direct lint test' not in commands
