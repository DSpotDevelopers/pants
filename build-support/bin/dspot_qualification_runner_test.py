# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from pathlib import Path

import yaml


def test_qualification_routes_docker_tests_to_an_admitted_runner() -> None:
    workflow = Path(__file__).resolve().parents[2] / ".github/workflows/dspot-pants.yaml"
    tests = yaml.safe_load(workflow.read_text())["jobs"]["tests"]
    assert {"heavy-ok", "docker-socket"} <= set(tests["runs-on"])
