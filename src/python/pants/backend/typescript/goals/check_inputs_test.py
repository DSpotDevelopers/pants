# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from pants.backend.typescript.goals import check
from pants.backend.typescript.goals.check import TypeScriptCheckFieldSet, TypeScriptCheckRequest
from pants.backend.typescript.goals.check_test_utils import _create_rule_runner, _load_project_test_files
from pants.build_graph.address import Address
from pants.core.goals.check import CheckResults
from pants.engine.fs import Snapshot
from pants.engine.process import Process


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
