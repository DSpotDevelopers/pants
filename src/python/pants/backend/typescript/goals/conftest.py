# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import cast

import pytest

from pants.backend.javascript.subsystems import nodejs_tool
from pants.backend.javascript.subsystems.nodejs import NodeJSBinaries
from pants.backend.typescript.goals.check_test_utils import (
    RuleRunnerWithProjectAndPackageManager,
    TestProjectAndPackageManager,
    _create_rule_runner,
)
from pants.engine.rules import QueryRule
from pants.testutil.rule_runner import RuleRunner


@pytest.fixture(scope="session")
def verified_nodejs_bin_dir() -> str:
    """Own one verified Node distribution; project runners retain their separate graphs and inputs."""
    bootstrap = RuleRunner(rules=[*nodejs_tool.rules(), QueryRule(NodeJSBinaries, [])])
    binaries = bootstrap.request(NodeJSBinaries, [])
    assert binaries.digest is not None
    prefix = "{chroot}/__node/"
    assert binaries.binary_dir.startswith(prefix)
    bootstrap.write_digest(binaries.digest, path_prefix="verified-node")
    binary_dir = str(
        Path(bootstrap.build_root, "verified-node", binaries.binary_dir.removeprefix(prefix))
    )
    subprocess.run(
        [str(Path(binary_dir, "corepack")), "enable", "npm", "pnpm", "yarn"],
        env={
            "PATH": os.pathsep.join((binary_dir, os.defpath)),
            "COREPACK_ENABLE_NETWORK": "0",
        },
        check=True,
        capture_output=True,
    )
    return binary_dir


@pytest.fixture(
    params=[("basic_project", "npm"), ("basic_project", "pnpm"), ("basic_project", "yarn")]
)
def basic_project_test(request) -> TestProjectAndPackageManager:
    return cast(TestProjectAndPackageManager, request.param)


@pytest.fixture(params=[("complex_project", "npm"), ("complex_project", "yarn")])
def complex_project_test(request) -> TestProjectAndPackageManager:
    return cast(TestProjectAndPackageManager, request.param)


@pytest.fixture(params=[("pnpm_link", "pnpm")])
def pnpm_project_test(request) -> TestProjectAndPackageManager:
    return cast(TestProjectAndPackageManager, request.param)


@pytest.fixture(params=[("pnpm_member_dep", "pnpm")])
def pnpm_member_dep_test(request) -> TestProjectAndPackageManager:
    return cast(TestProjectAndPackageManager, request.param)


@pytest.fixture
def basic_rule_runner(
    basic_project_test: TestProjectAndPackageManager,
    verified_nodejs_bin_dir: str,
) -> RuleRunnerWithProjectAndPackageManager:
    test_project, package_manager = basic_project_test
    return (
        _create_rule_runner(package_manager, verified_nodejs_bin_dir),
        test_project,
        package_manager,
    )


@pytest.fixture
def complex_proj_rule_runner(
    complex_project_test: TestProjectAndPackageManager,
    verified_nodejs_bin_dir: str,
) -> RuleRunnerWithProjectAndPackageManager:
    test_project, package_manager = complex_project_test
    return (
        _create_rule_runner(package_manager, verified_nodejs_bin_dir),
        test_project,
        package_manager,
    )


@pytest.fixture
def pnpm_rule_runner(
    pnpm_project_test: TestProjectAndPackageManager,
    verified_nodejs_bin_dir: str,
) -> RuleRunnerWithProjectAndPackageManager:
    test_project, package_manager = pnpm_project_test
    return (
        _create_rule_runner(package_manager, verified_nodejs_bin_dir),
        test_project,
        package_manager,
    )


@pytest.fixture
def pnpm_member_dep_rule_runner(
    pnpm_member_dep_test: TestProjectAndPackageManager,
    verified_nodejs_bin_dir: str,
) -> RuleRunnerWithProjectAndPackageManager:
    test_project, package_manager = pnpm_member_dep_test
    return (
        _create_rule_runner(package_manager, verified_nodejs_bin_dir),
        test_project,
        package_manager,
    )
