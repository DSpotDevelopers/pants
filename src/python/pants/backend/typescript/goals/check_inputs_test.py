# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any
from unittest.mock import patch

import pytest

from pants.backend.typescript.goals import check
from pants.backend.typescript.goals.check import TypeScriptCheckFieldSet, TypeScriptCheckRequest
from pants.backend.typescript.goals.check_test_utils import (
    RuleRunnerWithProjectAndPackageManager,
    _create_rule_runner,
    _load_project_test_files,
)
from pants.build_graph.address import Address
from pants.core.goals.check import CheckResults
from pants.engine.fs import CreateDigest, Digest, DigestEntries, FileContent, Snapshot, SymlinkEntry
from pants.engine.internals.native_engine import MergeDigests
from pants.engine.intrinsics import create_digest, merge_digests
from pants.engine.process import FallibleProcessResult, Process


def test_discovery_does_not_snapshot_cyclic_installed_workspace_links() -> None:
    runner = _create_rule_runner("pnpm")
    runner.write_files(_load_project_test_files("basic_project"))
    target = runner.get_target(
        Address("basic_project/src", target_name="ts_sources", relative_file_path="index.ts")
    )
    links = {
        SymlinkEntry("basic_project/first/node_modules/@test/second", "../../../second"),
        SymlinkEntry("basic_project/second/node_modules/@test/first", "../../../first"),
    }
    installed: set[Digest] = set()
    executions: list[Process] = []
    prepare = check.prepare_tool_process
    snapshot = check.digest_to_snapshot
    execute = check.execute_process

    async def install_links(*args: Any, **kwargs: Any) -> Process:
        process = await prepare(*args, **kwargs)
        workspace = await create_digest(
            CreateDigest(
                [
                    FileContent("basic_project/first/package.json", b'{"name":"@test/first"}'),
                    FileContent("basic_project/second/package.json", b'{"name":"@test/second"}'),
                    *links,
                ]
            )
        )
        digest = await merge_digests(MergeDigests([process.input_digest, workspace]))
        installed.add(digest)
        return replace(process, input_digest=digest)

    async def source_inventory(digest: Digest) -> Snapshot:
        # Refuse before walking the cycle, so the red control cannot exhaust its host.
        assert digest not in installed, "discovery snapshots the installed workspace cycle"
        return await snapshot(digest)

    async def capture_execution(process: Process, **kwargs: Any) -> FallibleProcessResult:
        executions.append(process)
        return await execute(process, **kwargs)

    with (
        patch.object(check, "prepare_tool_process", install_links),
        patch.object(check, "digest_to_snapshot", source_inventory),
        patch.object(check, "execute_process", capture_execution),
    ):
        results = runner.request(
            CheckResults, [TypeScriptCheckRequest([TypeScriptCheckFieldSet.create(target)])]
        )
    assert len(executions) == 2
    assert "--showConfig" in executions[0].argv
    assert "--build" in executions[1].argv
    for process in executions:
        entries = runner.request(DigestEntries, [process.input_digest])
        assert links.issubset(entries), "compiler process lost the installed workspace links"
    assert len(results.results) == 1
    result = results.results[0]
    assert result.exit_code == 0, result.stdout + result.stderr


def test_compiler_digest_excludes_unrelated_declared_assets() -> None:
    runner = _create_rule_runner("pnpm")
    files = _load_project_test_files("basic_project")
    unrelated = {
        "basic_project/misc/unrelated.whl": "x" * (1024 * 1024),
        "basic_project/misc/unrelated.json": '{"unrelated":true}',
        "basic_project/misc/unrelated.d.ts": "declare const unrelated: number;\n",
    }
    files.update(unrelated)
    files["basic_project/misc/BUILD"] = (
        "file(name='wheel', source='unrelated.whl')\n"
        "resource(name='json', source='unrelated.json')\n"
        "file(name='types', source='unrelated.d.ts')\n"
    )
    runner.write_files(files)
    target = runner.get_target(
        Address("basic_project/src", target_name="ts_sources", relative_file_path="index.ts")
    )
    original = check._prepare_tsc_build_process
    processes: list[Process] = []

    async def capture(*args: Any, **kwargs: Any) -> Process:
        process = await original(*args, **kwargs)
        processes.append(process)
        return process

    with patch.object(check, "_prepare_tsc_build_process", capture):
        results = runner.request(
            CheckResults, [TypeScriptCheckRequest([TypeScriptCheckFieldSet.create(target)])]
        )
    assert len(results.results) == 1
    result = results.results[0]
    assert result.exit_code == 0, result.stdout + result.stderr
    assert len(processes) == 1
    snapshot = runner.request(Snapshot, [processes[0].input_digest])
    unexpected = set(unrelated).intersection(snapshot.files)
    assert not unexpected, f"unrelated compiler inputs: {sorted(unexpected)}"
    assert "basic_project/src/index.ts" in snapshot.files


JS_TYPE_ERROR_FILE_NUMBER_TO_STRING = (
    'let x = "hello";\nx = 42; // Type error: cannot assign number to string\n'
)


def test_setting_typescript_version_emits_warning(
    basic_rule_runner: RuleRunnerWithProjectAndPackageManager, caplog
) -> None:
    rule_runner, test_project, package_manager = basic_rule_runner
    test_files = _load_project_test_files(test_project)
    rule_runner.write_files(test_files)

    rule_runner.set_options(
        [f"--nodejs-package-manager={package_manager}", "--typescript-version=typescript@5.0.0"],
        env_inherit={"PATH"},
    )

    target = rule_runner.get_target(
        Address("basic_project/src", target_name="ts_sources", relative_file_path="index.ts")
    )
    request = TypeScriptCheckRequest(field_sets=(TypeScriptCheckFieldSet.create(target),))
    rule_runner.request(CheckResults, [request])

    assert caplog.records
    assert "You set --typescript-version=typescript@5.0.0" in caplog.text
    assert "This setting is ignored because TypeScript always uses" in caplog.text


def test_check_javascript_enabled_via_tsconfig(
    basic_rule_runner: RuleRunnerWithProjectAndPackageManager,
) -> None:
    rule_runner, test_project, _ = basic_rule_runner
    test_files = _load_project_test_files(test_project)

    tsconfig_content = json.loads(test_files["basic_project/tsconfig.json"])
    tsconfig_content["compilerOptions"]["allowJs"] = True
    tsconfig_content["compilerOptions"]["checkJs"] = True
    test_files["basic_project/tsconfig.json"] = json.dumps(tsconfig_content, indent=2)

    test_files["basic_project/src/error.js"] = JS_TYPE_ERROR_FILE_NUMBER_TO_STRING
    test_files["basic_project/src/BUILD"] = (
        'javascript_sources(name="js_sources")\ntypescript_sources()\n'
    )

    rule_runner.write_files(test_files)

    js_target = rule_runner.get_target(
        Address("basic_project/src", target_name="js_sources", relative_file_path="error.js")
    )
    request = TypeScriptCheckRequest(field_sets=(TypeScriptCheckFieldSet.create(js_target),))
    results = rule_runner.request(CheckResults, [request])

    assert len(results.results) == 1
    assert results.results[0].exit_code != 0
    assert "error.js" in results.results[0].stdout
    assert "Type 'number' is not assignable to type 'string'" in results.results[0].stdout


def test_check_javascript_disabled_via_tsconfig(
    basic_rule_runner: RuleRunnerWithProjectAndPackageManager,
) -> None:
    rule_runner, test_project, _ = basic_rule_runner
    test_files = _load_project_test_files(test_project)

    # Use the same JS file with type error that would be caught if processed
    test_files["basic_project/src/error.js"] = JS_TYPE_ERROR_FILE_NUMBER_TO_STRING
    test_files["basic_project/src/BUILD"] = (
        'javascript_sources(name="js_sources")\ntypescript_sources()\n'
    )

    rule_runner.write_files(test_files)

    js_target = rule_runner.get_target(
        Address("basic_project/src", target_name="js_sources", relative_file_path="error.js")
    )
    request = TypeScriptCheckRequest(field_sets=(TypeScriptCheckFieldSet.create(js_target),))
    results = rule_runner.request(CheckResults, [request])

    assert len(results.results) == 1
    assert results.results[0].exit_code == 0
    assert "error.js" not in results.results[0].stdout


@pytest.mark.parametrize("module_kind", ["javascript", "resource", "declaration", "ambient"])
def test_compiler_receives_imported_inputs(module_kind: str) -> None:
    rule_runner = _create_rule_runner("pnpm")
    files = _load_project_test_files("basic_project")
    config = json.loads(files["basic_project/tsconfig.json"])
    config["compilerOptions"].update(allowJs=True, checkJs=False, resolveJsonModule=True)
    files["basic_project/tsconfig.json"] = json.dumps(config)
    if module_kind == "ambient":
        files["basic_project/src/index.ts"] = (
            "import {answer} from 'virtual:answer';\nexport const result: number = answer;\n"
        )
        files["basic_project/src/virtual.d.ts"] = (
            "declare module 'virtual:answer' {export const answer: number;}\n"
        )
        files["basic_project/src/BUILD"] += '\nfile(name="types", source="virtual.d.ts")\n'
    elif module_kind == "resource":
        # Composite projects require JSON inputs to be named explicitly in include, even
        # when another include pattern already covers their containing directory.
        config["include"].append("src/**/*.json")
        files["basic_project/tsconfig.json"] = json.dumps(config)
        files["basic_project/src/index.ts"] = (
            "import data from './values.json';\nexport const answer: number = data.answer;\n"
        )
        files["basic_project/src/values.json"] = '{"answer": 42}'
        files["basic_project/src/BUILD"] += '\nresource(name="values", source="values.json")\n'
    else:
        files["basic_project/src/index.ts"] = (
            "import {answer} from './values.mjs';\nexport const result: number = answer;\n"
        )
        files["basic_project/src/values.mjs"] = "export const answer = 42;\n"
        files["basic_project/src/BUILD"] += '\njavascript_sources(name="js")\n'
        if module_kind == "declaration":
            # A declaration beside a JS module participates even when checkJs is false.
            files["basic_project/src/values.mjs"] = "export const answer = 'runtime';\n"
            files["basic_project/src/values.d.mts"] = "export declare const answer: number;\n"
            files["basic_project/src/BUILD"] += '\nfile(name="types", source="values.d.mts")\n'
    rule_runner.write_files(files)
    target = rule_runner.get_target(
        Address("basic_project/src", target_name="ts_sources", relative_file_path="index.ts")
    )
    results = rule_runner.request(
        CheckResults, [TypeScriptCheckRequest([TypeScriptCheckFieldSet.create(target)])]
    )
    assert len(results.results) == 1
    result = results.results[0]
    assert result.exit_code == 0, result.stdout + result.stderr


def test_javascript_only_project_does_not_require_a_typescript_compiler() -> None:
    rule_runner = _create_rule_runner("pnpm")
    rule_runner.write_files(
        {
            "BUILD": "package_json(name='workspace')\njavascript_sources(name='js')\n",
            "package.json": '{"name":"javascript-only","private":true}',
            "index.js": "export const answer = 42;\n",
        }
    )
    target = rule_runner.get_target(Address("", target_name="js", relative_file_path="index.js"))
    results = rule_runner.request(
        CheckResults, [TypeScriptCheckRequest([TypeScriptCheckFieldSet.create(target)])]
    )
    assert len(results.results) == 1
    assert results.results[0].exit_code == 0


def test_typescript_check_resolves_member_only_deps(
    pnpm_member_dep_rule_runner: RuleRunnerWithProjectAndPackageManager,
) -> None:
    """Regression test: @types/node is declared only on the member, not the root.

    Pre-fix, tsc ran from the workspace root and couldn't see member/node_modules,
    so it failed with TS2304 (Cannot find name 'process').
    """
    rule_runner, test_project, _ = pnpm_member_dep_rule_runner
    test_files = _load_project_test_files(test_project)
    rule_runner.write_files(test_files)

    target = rule_runner.get_target(
        Address(
            f"{test_project}/member/src",
            target_name="ts_sources",
            relative_file_path="node_types.ts",
        )
    )
    field_set = TypeScriptCheckFieldSet.create(target)
    request = TypeScriptCheckRequest([field_set])
    results = rule_runner.request(CheckResults, [request])

    assert len(results.results) == 1
    result = results.results[0]
    assert result.exit_code == 0, (
        f"TypeScript check failed — member node_modules likely missing from sandbox:\n"
        f"{result.stdout}\n{result.stderr}"
    )
