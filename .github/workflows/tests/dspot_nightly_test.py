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


def test_it_installs_the_interpreters_the_tests_job_installs() -> None:
    (mine,) = _uses(_job(), "actions/setup-python@")
    (theirs,) = _uses(_load(PR_RUN)["jobs"]["tests"], "actions/setup-python@")
    assert mine["with"]["python-version"].split() == theirs["with"]["python-version"].split()


def test_MUST_FIRE_it_tests_every_target_of_the_qualified_scope_not_a_change() -> None:
    (step,) = [s for s in _job()["steps"] if "./pants" in s.get("run", "")]
    script = step["run"]
    assert "dspot_qualified_selection.py --all" in script
    assert "--spec-files=" in script and " test" in script
    assert "--changed-since" not in script and "--changed-dependents" not in script
    deselect = _load(PR_RUN)["jobs"]["tests"]["steps"]
    (theirs,) = [s for s in deselect if "./pants" in s.get("run", "")]
    assert step["env"]["PANTS_PYTEST_ARGS"] == theirs["env"]["PANTS_PYTEST_ARGS"]
