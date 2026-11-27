# Copyright 2023 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

import hashlib
import shutil
import sys
from pathlib import Path

import pytest

from pants.build_graph.address import Address
from pants.core.environments.target_types import (
    DockerEnvironmentTarget,
    EnvironmentTarget,
    LocalEnvironmentTarget,
)
from pants.core.util_rules import adhoc_binaries
from pants.core.util_rules.adhoc_binaries import (
    _DownloadPythonBuildStandaloneBinaryRequest,
    _PythonBuildStandaloneBinary,
)
from pants.engine.environment import EnvironmentName
from pants.engine.platform import Platform
from pants.testutil.rule_runner import QueryRule, RuleRunner, run_rule_with_mocks


@pytest.fixture
def rule_runner() -> RuleRunner:
    return RuleRunner(
        rules=[
            *adhoc_binaries.rules(),
            QueryRule(
                _PythonBuildStandaloneBinary,
                [_DownloadPythonBuildStandaloneBinaryRequest],
            ),
        ],
        target_types=[LocalEnvironmentTarget, DockerEnvironmentTarget],
    )


@pytest.mark.parametrize("env_tgt", [None, LocalEnvironmentTarget({}, address=Address(""))])
def test_local(env_tgt) -> None:
    def mock_download_python_binary(
        _: _DownloadPythonBuildStandaloneBinaryRequest,
    ) -> _PythonBuildStandaloneBinary:
        pytest.fail()

    result = run_rule_with_mocks(
        adhoc_binaries.get_python_for_scripts,
        rule_args=[EnvironmentTarget("local", env_tgt)],
        mock_calls={
            "pants.core.util_rules.adhoc_binaries.download_python_binary": mock_download_python_binary,
        },
    )
    assert result == adhoc_binaries.PythonBuildStandaloneBinary(sys.executable)


def test_docker_uses_helper(rule_runner: RuleRunner, tmp_path: Path) -> None:
    # Exercise archive verification, extraction and installation without an external release download.
    python = tmp_path / "python" / "bin" / "python3"
    python.parent.mkdir(parents=True)
    python.write_text("#!/bin/sh\nexit 0\n")
    python.chmod(0o755)
    archive = Path(shutil.make_archive(str(tmp_path / "pbs"), "gztar", tmp_path, "python"))
    info = {
        Platform.create_for_localhost().for_linux().value: (
            archive.as_uri(),
            hashlib.sha256(archive.read_bytes()).hexdigest(),
            archive.stat().st_size,
        )
    }
    rule_runner = RuleRunner(
        rules=[
            *adhoc_binaries.rules(),
            QueryRule(
                _PythonBuildStandaloneBinary,
                [_DownloadPythonBuildStandaloneBinaryRequest],
            ),
        ],
        target_types=[DockerEnvironmentTarget],
        inherent_environment=EnvironmentName("docker"),
    )
    rule_runner.write_files(
        {
            "BUILD": "docker_environment(name='docker', image='ubuntu:latest')",
        }
    )
    rule_runner.set_options(
        [
            "--environments-preview-names={'docker': '//:docker'}",
            f"--python-bootstrap-internal-python-build-standalone-info={info!r}",
        ],
        env_inherit={"PATH"},
    )
    pbs = rule_runner.request(
        _PythonBuildStandaloneBinary,
        [_DownloadPythonBuildStandaloneBinaryRequest()],
    )
    assert pbs.path.startswith("/pants-named-caches")
    assert pbs.path.endswith("/bin/python3")
