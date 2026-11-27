# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""The selected pytest runner integration cells need Python 3.13 on the test host."""

from pathlib import Path

import yaml


def test_tests_job_installs_python_313_for_pytest_runner_cells() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/dspot-pants.yaml").read_text())
    setup = [
        step
        for step in workflow["jobs"]["tests"]["steps"]
        if step.get("uses", "").startswith("actions/setup-python@")
    ]
    assert len(setup) == 1
    versions = {".".join(value.split(".")[:2]) for value in setup[0]["with"]["python-version"].split()}
    assert "3.13" in versions
