# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import annotations

from dspot_qualified_selection import ALWAYS_LOADED, register_module, scope, selection

# Environment kinds whose suites the guarded runners run: no job there owns a Docker host path, and
# none reaches a remote execution service.
RUNNABLE_ENVIRONMENTS = {"local_environment", "experimental_workspace_environment"}


def fake_pants(loaded: list[str], changed: list[str]):
    calls = []

    def pants(*args: str) -> list[str]:
        calls.append(args)
        return loaded if args[0] == "dependencies" else changed

    return pants, calls


def test_the_selection_keeps_core_and_the_loaded_backends_only() -> None:
    pants, calls = fake_pants(
        loaded=[
            "src/python/pants/backend/python/util_rules/pex.py",
            "src/python/pants/backend/adhoc:adhoc",
            "src/python/pants/engine/rules.py",
        ],
        changed=[
            "src/python/pants/engine/rules_test.py:tests",
            "src/python/pants/backend/python/util_rules/pex_test.py",
            "src/python/pants/backend/adhoc/run_system_binary_test.py",
            "src/python/pants/backend/docker/util_rules/docker_build_context_test.py",
            "src/python/pants/backend/go/goals/test_test.py",
            "src/python/pants/backend/python:python",
            "src/python/pants:wheel-definition",
        ],
    )
    assert selection(pants, "base") == (
        [
            "src/python/pants/engine/rules_test.py:tests",
            "src/python/pants/backend/python/util_rules/pex_test.py",
            "src/python/pants/backend/adhoc/run_system_binary_test.py",
            "src/python/pants/backend/python:python",
            "src/python/pants:wheel-definition",
        ],
        [
            "src/python/pants/backend/docker/util_rules/docker_build_context_test.py",
            "src/python/pants/backend/go/goals/test_test.py",
        ],
    )
    roots = [register_module(b) for b in (*ALWAYS_LOADED, *scope()["backend_packages"])]
    assert calls == [
        ("dependencies", "--transitive", *roots),
        ("--changed-since=base", "--changed-dependents=direct", "list"),
    ]


def test_the_scope_names_only_environments_the_runners_qualify() -> None:
    # A Docker or remote environment can't run on these runners: adding one to the scope (because
    # the company declared it) needs a runner for it first, never a skip.
    assert set(scope()["environment_targets"]) <= RUNNABLE_ENVIRONMENTS
