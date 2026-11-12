# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import annotations

from pathlib import Path

from pants.backend.javascript import package_json
from pants.backend.javascript.subsystems import nodejs_tool
from pants.backend.javascript.target_types import JSSourcesGeneratorTarget
from pants.backend.tsx.target_types import TSXSourcesGeneratorTarget, TSXTestsGeneratorTarget
from pants.backend.typescript.goals import check
from pants.backend.typescript.goals.check import TypeScriptCheckRequest
from pants.backend.typescript.target_types import (
    TypeScriptSourcesGeneratorTarget,
    TypeScriptTestsGeneratorTarget,
)
from pants.core.goals import package
from pants.core.goals.check import CheckResults
from pants.core.target_types import FileTarget, ResourceTarget
from pants.engine.fs import Digest, DigestEntries
from pants.engine.rules import QueryRule
from pants.testutil.rule_runner import RuleRunner

TestProjectAndPackageManager = tuple[str, str]
RuleRunnerWithProjectAndPackageManager = tuple[RuleRunner, str, str]


def _create_rule_runner(package_manager: str) -> RuleRunner:
    rule_runner = RuleRunner(
        rules=[
            *nodejs_tool.rules(),
            *check.rules(),
            *package.rules(),
            QueryRule(CheckResults, [TypeScriptCheckRequest]),
            QueryRule(DigestEntries, [Digest]),
        ],
        target_types=[
            package_json.PackageJsonTarget,
            JSSourcesGeneratorTarget,
            TypeScriptSourcesGeneratorTarget,
            TypeScriptTestsGeneratorTarget,
            TSXSourcesGeneratorTarget,
            TSXTestsGeneratorTarget,
            FileTarget,
            ResourceTarget,
        ],
        objects=dict(package_json.build_file_aliases().objects),
    )
    rule_runner.set_options(
        [f"--nodejs-package-manager={package_manager}"],
        env_inherit={"PATH"},
    )
    return rule_runner


def _load_project_test_files(test_project: str) -> dict[str, str]:
    base_dir = Path(__file__).parent.parent / "test_resources" / test_project
    files = {}

    for file_path in base_dir.rglob("*"):
        if file_path.is_file():
            relative_path = file_path.relative_to(base_dir)
            files[f"{test_project}/{relative_path}"] = file_path.read_text()

    return files
