# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import annotations

from dspot_qualified_selection import ALWAYS_LOADED, ENTRY, register_module, scope, selection

# Environment kinds whose suites the guarded runners run: no job there owns a Docker host path, and
# none reaches a remote execution service.
RUNNABLE_ENVIRONMENTS = {"local_environment", "experimental_workspace_environment"}


def fake_pants(loaded: list[str], changed: list[str]):
    calls = []

    def pants(*args: str) -> list[str]:
        calls.append(args)
        return loaded if args[0] == "dependencies" else changed

    return pants, calls


def test_the_selection_keeps_the_folders_pants_loads_with_our_backends() -> None:
    pants, calls = fake_pants(
        loaded=[
            "src/python/pants/backend/python/util_rules/pex.py",
            "src/python/pants/backend/adhoc:adhoc",
            "src/python/pants/engine/rules.py",
            "src/python/pants/version.py",
        ],
        changed=[
            "src/python/pants/engine/rules_test.py:tests",
            "src/python/pants/backend/python/util_rules/pex_test.py",
            "src/python/pants/backend/adhoc/run_system_binary_test.py",
            "src/python/pants/backend/docker/util_rules/docker_build_context_test.py",
            "src/python/pants/backend/go/goals/test_test.py",
            "src/python/pants/backend/python:python",
            "src/python/pants:wheel-definition",
            "src/python/pants/jvm/jdk_rules_test.py:tests",
            "src/python/pants/engine/internals/buildbarn_integration_tests/buildbarn_remote_cache_integration_test.py:tests",
            ".github/workflows/tests/dspot_pants_trust_test.py",
            "build-support/bin/dspot_slot_cpus_test.py",
        ],
    )
    assert selection(pants, "base") == (
        [
            "src/python/pants/engine/rules_test.py:tests",
            "src/python/pants/backend/python/util_rules/pex_test.py",
            "src/python/pants/backend/adhoc/run_system_binary_test.py",
            "src/python/pants/backend/python:python",
            "src/python/pants:wheel-definition",
            ".github/workflows/tests/dspot_pants_trust_test.py",
            "build-support/bin/dspot_slot_cpus_test.py",
        ],
        [
            "src/python/pants/backend/docker/util_rules/docker_build_context_test.py",
            "src/python/pants/backend/go/goals/test_test.py",
            "src/python/pants/jvm/jdk_rules_test.py:tests",
            "src/python/pants/engine/internals/buildbarn_integration_tests/buildbarn_remote_cache_integration_test.py:tests",
        ],
    )
    roots = [ENTRY, *(register_module(b) for b in (*ALWAYS_LOADED, *scope()["backend_packages"]))]
    assert calls == [
        ("dependencies", "--transitive", *roots),
        ("--changed-since=base", "--changed-dependents=direct", "list"),
    ]


def test_the_scope_names_only_environments_the_runners_qualify() -> None:
    # A Docker or remote environment can't run on these runners: adding one to the scope (because
    # the company declared it) needs a runner for it first, never a skip.
    assert set(scope()["environment_targets"]) <= RUNNABLE_ENVIRONMENTS


def test_the_entry_root_is_pants_code_not_its_release_bundle() -> None:
    # a target of bin's folder would bring every backend: pants_loader's depends on `:plugins`, and
    # the folder's other target holds its tests, which reach pants_loader through pants/__main__.py
    assert ENTRY == "src/python/pants/bin/pants_runner.py"
    assert ":" not in ENTRY and not ENTRY.endswith("_test.py")


DOCKER_CELLS = '''
from textwrap import dedent


def _runner(image):
    runner = RuleRunner(
        inherent_environment=EnvironmentName("test-env") if image else EnvironmentName(None)
    )
    if image:
        runner.write_files({"BUILD": f"docker_environment(name='test-env', image='{image}')"})
        runner.set_options(["--environments-preview-names={'test-env': '//:test-env'}"])
    return runner


def test_local_through_the_helper():
    _runner(image=None)


def test_docker_through_the_helper():
    _runner(image="python:3.14-slim")


def test_runs_in_docker():
    runner = RuleRunner(inherent_environment=EnvironmentName("docker"))
    runner.write_files({"BUILD": "docker_environment(\\n    name='docker',\\n    image='ubuntu')"})
    runner.set_options(["--environments-preview-names={'docker': '//:docker'}"])


def test_a_target_runs_in_docker(dirname):
    files = {
        "project/BUILD": "python_tests(environment='py310')",
        "BUILD": dedent(
            """\\
            docker_environment(
                name="py310",
                image="python:3.10",
            )
            """
        ),
    }
    run([f"--environments-preview-names={{'py310': '{dirname}:py310'}}"])


def test_chooses_among_environments(rule_runner):
    rule_runner.write_files(
        {
            "BUILD": dedent(
                """\\
                local_environment(name='e1')
                docker_environment(name='docker', image="centos6:latest")
                remote_environment(name='remote', fallback_environment="docker")
                """
            )
        }
    )
    rule_runner.set_options(["--environments-preview-names={'e1': '//:e1', 'docker': '//:docker'}"])


class TestRemote:
    def test_runs_remotely(self):
        runner = RuleRunner(inherent_environment=EnvironmentName("rbe"))
        runner.write_files({"BUILD": "remote_environment(name='rbe')"})
        runner.set_options(["--environments-preview-names={'rbe': '//:rbe'}"])

    def test_runs_in_the_workspace(self):
        runner = RuleRunner(inherent_environment=EnvironmentName("ws"))
        runner.write_files({"BUILD": "experimental_workspace_environment(name='ws')"})
        runner.set_options(["--environments-preview-names={'ws': '//:ws'}"])
'''


def test_a_cell_whose_processes_run_in_an_environment_outside_the_contract_is_left_out(
    tmp_path, monkeypatch
) -> None:
    from dspot_qualified_selection import unqualified_cells

    (tmp_path / "src/python/pants/core").mkdir(parents=True)
    (tmp_path / "src/python/pants/core/rules_test.py").write_text(DOCKER_CELLS)
    monkeypatch.chdir(tmp_path)
    selected = ["src/python/pants/core/rules_test.py:tests", "src/python/pants/core:core"]
    assert unqualified_cells(selected, {"docker_environment", "remote_environment"}) == [
        "src/python/pants/core/rules_test.py::test_docker_through_the_helper",
        "src/python/pants/core/rules_test.py::test_runs_in_docker",
        "src/python/pants/core/rules_test.py::test_a_target_runs_in_docker",
        "src/python/pants/core/rules_test.py::TestRemote::test_runs_remotely",
    ]


def test_the_environment_kinds_are_read_from_pants_own_target_types() -> None:
    from dspot_qualified_selection import environment_kinds

    target_types = (
        "class FallbackEnvironmentField(StringField):\n"
        '    alias = "fallback_environment"\n'
        "class LocalEnvironmentTarget(Target):\n"
        '    alias = "local_environment"\n'
        "class DockerImageField(StringField):\n"
        '    alias = "image"\n'
        "class DockerEnvironmentTarget(Target):\n"
        '    alias = "docker_environment"\n'
    )
    assert environment_kinds(target_types) == {"local_environment", "docker_environment"}


def test_the_left_out_cells_are_pytest_args_appended_to_the_configured_ones() -> None:
    from dspot_qualified_selection import pytest_args

    assert pytest_args(["a_test.py::test_x", "b_test.py::T::test_y"]) == (
        '+["--deselect=a_test.py::test_x", "--deselect=b_test.py::T::test_y"]'
    )
    assert pytest_args([]) == "+[]"
