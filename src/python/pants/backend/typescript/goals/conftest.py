# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import annotations

from typing import cast

import pytest

from pants.backend.typescript.goals.check_test_utils import (
    RuleRunnerWithProjectAndPackageManager,
    TestProjectAndPackageManager,
    _create_rule_runner,
)


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
) -> RuleRunnerWithProjectAndPackageManager:
    test_project, package_manager = basic_project_test
    return _create_rule_runner(package_manager), test_project, package_manager


@pytest.fixture
def complex_proj_rule_runner(
    complex_project_test: TestProjectAndPackageManager,
) -> RuleRunnerWithProjectAndPackageManager:
    test_project, package_manager = complex_project_test
    return _create_rule_runner(package_manager), test_project, package_manager


@pytest.fixture
def pnpm_rule_runner(
    pnpm_project_test: TestProjectAndPackageManager,
) -> RuleRunnerWithProjectAndPackageManager:
    test_project, package_manager = pnpm_project_test
    return _create_rule_runner(package_manager), test_project, package_manager


@pytest.fixture
def pnpm_member_dep_rule_runner(
    pnpm_member_dep_test: TestProjectAndPackageManager,
) -> RuleRunnerWithProjectAndPackageManager:
    test_project, package_manager = pnpm_member_dep_test
    return _create_rule_runner(package_manager), test_project, package_manager
