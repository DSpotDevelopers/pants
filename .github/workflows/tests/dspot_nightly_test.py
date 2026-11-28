# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""DSpot's nightly full run: every suite of the qualified scope, once a day and on demand.

A pull request runs its change and the change's direct dependents (dspot-pants.yaml's `tests` job). A change that
reaches hundreds of suites, such as an edit to a BUILD file most of Pants depends on, qualifies here instead: the
same scope (build-support/bin/dspot_qualification_scope.toml), the same runner class and interpreters, every target.
"""

from __future__ import annotations

from pathlib import Path

import yaml

NIGHTLY = Path(".github/workflows/dspot-pants-nightly.yaml")
PR_RUN = Path(".github/workflows/dspot-pants.yaml")


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def _job() -> dict:
    (job,) = _load(NIGHTLY)["jobs"].values()
    return job


def _uses(job: dict, action: str) -> list[dict]:
    return [s for s in job["steps"] if s.get("uses", "").startswith(action)]


def test_it_runs_once_a_day_and_on_demand_never_on_a_pull_request() -> None:
    # PyYAML reads the key `on` as True.
    triggers = _load(NIGHTLY)[True]
    assert set(triggers) == {"schedule", "workflow_dispatch"}
    (schedule,) = triggers["schedule"]
    assert len(schedule["cron"].split()) == 5


def test_it_runs_on_the_tests_jobs_own_runner_class() -> None:
    assert _job()["runs-on"] == _load(PR_RUN)["jobs"]["tests"]["runs-on"]


def _minor(version: str) -> str:
    return ".".join(version.split(".")[:2])


def missing_setup(nightly: dict, tests: dict) -> list[str]:
    """What the tests job installs that the nightly does not: every `actions/setup-*` step (setup-python by the
    interpreters' major.minor) and every build-support/bin/dspot_*.sh installer it runs. The full run reaches every
    suite the tests job can, so it needs at least the same environment."""
    missing = []
    for step in tests["steps"]:
        action = step.get("uses", "").split("@")[0]
        if action == "actions/setup-python":
            have = {
                _minor(v)
                for s in _uses(nightly, "actions/setup-python@")
                for v in s["with"]["python-version"].split()
            }
            missing += [
                f"python {_minor(v)}"
                for v in step["with"]["python-version"].split()
                if _minor(v) not in have
            ]
        elif action.startswith("actions/setup-") and not any(
            s.get("uses", "").split("@")[0] == action and s.get("with") == step.get("with")
            for s in nightly["steps"]
        ):
            missing.append(action)
        for word in step.get("run", "").split():
            if (
                word.startswith("build-support/bin/dspot_")
                and word.endswith(".sh")
                and not any(word in s.get("run", "") for s in nightly["steps"])
            ):
                missing.append(word)
    return missing


def test_it_installs_at_least_what_the_tests_job_installs() -> None:
    assert missing_setup(_job(), _load(PR_RUN)["jobs"]["tests"]) == []


def test_MUST_FIRE_a_tests_job_installer_the_nightly_lacks_is_named() -> None:
    tests = {
        "steps": [
            {
                "uses": "actions/setup-java@0",
                "with": {"distribution": "adopt", "java-version": "11"},
            },
            {"uses": "actions/setup-python@0", "with": {"python-version": "3.8\n3.99"}},
            {"run": "build-support/bin/dspot_ci_python.sh"},
        ]
    }
    nightly = {"steps": [{"uses": "actions/setup-python@1", "with": {"python-version": "3.8.18"}}]}
    assert missing_setup(nightly, tests) == [
        "actions/setup-java",
        "python 3.99",
        "build-support/bin/dspot_ci_python.sh",
    ]


def test_it_installs_the_jdk_and_interpreters_the_whole_scope_needs() -> None:
    # Every suite outside src/python/pants/backend/ is in scope, so pants/jvm and pants/bsp are, and they need a JDK;
    # the interpreter-dependent suites need each Python Pants supports.
    (java,) = _uses(_job(), "actions/setup-java@")
    assert java["with"] == {"distribution": "adopt", "java-version": "11"}
    (python,) = _uses(_job(), "actions/setup-python@")
    versions = python["with"]["python-version"].split()
    assert {"3.8", "3.9", "3.10", "3.11", "3.12", "3.13"} <= {_minor(v) for v in versions}


def test_MUST_FIRE_pants_runs_on_the_pinned_standalone_python_as_in_the_tests_job() -> None:
    # The tests job's default python is the pinned standalone install (build-support/bin/dspot_ci_python.sh writes PY and
    # its bin to the job's environment); the nightly runs Pants on the same one, never setup-python's 3.14.
    steps = _job()["steps"]
    (python,) = _uses(_job(), "actions/setup-python@")
    assert "3.14" not in {_minor(v) for v in python["with"]["python-version"].split()}
    installer = [i for i, s in enumerate(steps) if "build-support/bin/dspot_ci_python.sh" in s.get("run", "")]
    assert installer == [steps.index(python) + 1], "the pinned installer runs right after setup-python"
    assert "PY" not in _job().get("env", {}), "PY is the pinned install's, written by the installer"
    first_py = next(i for i, s in enumerate(steps) if '"$PY"' in s.get("run", ""))
    assert installer[0] < first_py


def test_MUST_FIRE_it_tests_every_target_of_the_qualified_scope_not_a_change() -> None:
    (step,) = [s for s in _job()["steps"] if "./pants" in s.get("run", "")]
    script = step["run"]
    assert "dspot_qualified_selection.py --all" in script
    assert "--spec-files=" in script and " test" in script
    assert "--changed-since" not in script and "--changed-dependents" not in script
    deselect = _load(PR_RUN)["jobs"]["tests"]["steps"]
    (theirs,) = [s for s in deselect if "./pants" in s.get("run", "")]
    assert step["env"]["PANTS_PYTEST_ARGS"] == theirs["env"]["PANTS_PYTEST_ARGS"]
