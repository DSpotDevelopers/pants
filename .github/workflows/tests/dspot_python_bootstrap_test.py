# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""The CI bootstrap cannot depend on another runner's interpreter or shell's loader path."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


def test_venv_identity_follows_the_real_interpreter(tmp_path: Path) -> None:
    interpreters = []
    for name in ("first", "second"):
        target = tmp_path / name / "python"
        target.parent.mkdir()
        shutil.copy2(Path(sys.executable).resolve(), target)
        interpreters.append(target)
    alias = tmp_path / "alias"
    alias.symlink_to(interpreters[0])

    def venv(python: Path) -> str:
        return subprocess.check_output(
            ["bash", "-c", "source build-support/pants_venv; venv_dir"],
            env={**os.environ, "PY": str(python), "PYTHONHOME": sys.base_prefix},
            text=True,
        ).strip()

    assert venv(interpreters[0]) == venv(alias), "aliases share the same interpreter"
    assert venv(interpreters[0]) != venv(interpreters[1]), (
        "different installations must not share a venv"
    )


def test_both_jobs_use_the_same_self_contained_python() -> None:
    jobs = yaml.safe_load(Path(".github/workflows/dspot-pants.yaml").read_text())["jobs"]
    for name in ("build", "tests"):
        steps = jobs[name]["steps"]
        bootstrap = [s for s in steps if s.get("run") == "build-support/bin/dspot_ci_python.sh"]
        assert len(bootstrap) == 1, name
        assert "PY" not in jobs[name]["env"], "the bootstrap publishes the pinned absolute path"
        assert steps.index(bootstrap[0]) < next(
            i
            for i, step in enumerate(steps)
            if "./pants" in step.get("run", "")
            or step.get("run") == "build-support/bin/dspot_release_build.sh"
        )


def test_bootstrap_proof_covers_both_runner_classes() -> None:
    jobs = yaml.safe_load(Path(".github/workflows/dspot-pants.yaml").read_text())["jobs"]
    job = jobs["python-bootstrap"]
    matrix = job["strategy"]["matrix"]
    rows = matrix.get("include") or [{"runner-class": name} for name in matrix["runner-class"]]
    # The company medium lane requests these four labels. Only heavy runners carry "dspot".
    fleet_labels = {
        "heavy-ok": {"self-hosted", "linux", "x64", "dspot", "heavy-ok"},
        "slot-medium": {"self-hosted", "linux", "x64", "slot-medium"},
    }
    assert {row["runner-class"] for row in rows} == set(fleet_labels)
    for row in rows:
        configured = job["runs-on"]
        labels = (
            row["runner-labels"]
            if configured == "${{ matrix.runner-labels }}"
            else [
                label.replace("${{ matrix.runner-class }}", row["runner-class"])
                for label in configured
            ]
        )
        assert set(labels) == fleet_labels[row["runner-class"]], row["runner-class"]
    assert "python-bootstrap" in jobs["build"]["needs"]


def test_selected_backend_suites_require_the_guarded_docker_socket() -> None:
    jobs = yaml.safe_load(Path(".github/workflows/dspot-pants.yaml").read_text())["jobs"]
    assert "docker-socket" in jobs["tests"]["runs-on"]
