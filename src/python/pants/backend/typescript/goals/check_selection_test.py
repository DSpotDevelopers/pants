# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import annotations

import json

import pytest

from pants.backend.typescript.goals.check import TypeScriptCheckFieldSet, TypeScriptCheckRequest
from pants.backend.typescript.goals.check_test_utils import (
    _create_rule_runner,
    _load_project_test_files,
)
from pants.build_graph.address import Address
from pants.core.goals.check import CheckResults


@pytest.mark.parametrize("config_style", ["directory", "named", "arbitrary"])
@pytest.mark.parametrize("selection", ["clean", "broken", "dependency", "both"])
def test_check_selects_tsconfig_program_without_unrelated_sibling(
    config_style: str, selection: str
) -> None:
    rule_runner = _create_rule_runner("pnpm")
    named_config = config_style != "directory"
    files = _load_project_test_files("basic_project")
    compiler_options = json.loads(files["basic_project/tsconfig.json"])["compilerOptions"]
    compiler_options["composite"] = True
    compiler_options["rootDir"] = "../src" if named_config else "."
    selected_config = (
        "configs/workflow-tests.json"
        if config_style == "arbitrary"
        else "configs/tsconfig.workflow-tests.json"
        if named_config
        else "src/tsconfig.json"
    )
    if config_style == "arbitrary":
        files["basic_project/configs/BUILD"] = "file(name='config', source='workflow-tests.json')\n"
    files["basic_project/tsconfig.json"] = json.dumps(
        {
            "files": [],
            "references": [{"path": selected_config}, {"path": "other"}],
            "compilerOptions": {"outDir": "./dist"},
        }
    )
    selected = {
        "compilerOptions": compiler_options,
        "include": ["../src/**/*.ts" if named_config else "*.ts"],
    }
    if selection == "dependency":
        selected["references"] = [{"path": "../other"}]
    files["basic_project/" + selected_config] = json.dumps(selected)
    files["basic_project/other/tsconfig.json"] = json.dumps(
        {"compilerOptions": {**compiler_options, "rootDir": "."}, "include": ["*.ts"]}
    )
    files["basic_project/other/BUILD"] = "typescript_sources(name='ts_sources')\n"
    files["basic_project/other/broken.ts"] = "export const broken: string = 42;\n"
    rule_runner.write_files(files)
    directory, filename = ("other", "broken.ts") if selection == "broken" else ("src", "index.ts")
    target = rule_runner.get_target(
        Address("basic_project/" + directory, target_name="ts_sources", relative_file_path=filename)
    )
    field_sets = [TypeScriptCheckFieldSet.create(target)]
    if selection == "both":
        other = rule_runner.get_target(
            Address("basic_project/other", target_name="ts_sources", relative_file_path="broken.ts")
        )
        field_sets.append(TypeScriptCheckFieldSet.create(other))
    results = rule_runner.request(CheckResults, [TypeScriptCheckRequest(field_sets)])
    assert len(results.results) == 1
    result = results.results[0]
    if selection == "clean":
        assert result.exit_code == 0, result.stdout + result.stderr
    else:
        assert result.exit_code != 0
        assert "TS2322" in result.stdout + result.stderr
