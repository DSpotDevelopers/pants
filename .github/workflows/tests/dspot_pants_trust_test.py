# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""Who may start DSpot's Pants build (dspot-pants.yaml) on a pull request.

The build runs on our self-hosted runners under `pull_request_target`, so it starts only for a pull request from this
repository whose author is trusted: an owner, member or collaborator of it, or the one GitHub App our worker lines open
pull requests as, named by its exact login. Any other author, bots included, never starts it. The rule lives in the
`source` job alone (its `if` and its script, which also guards a dispatch); every other job reaches the pull request
only through `needs: source`, so it cannot run when `source` did not.
"""

from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOW = Path(".github/workflows/dspot-pants.yaml")
APP = "dspot-worker-lines[bot]"
GATE_WORDS = ("author_association", "user.login")


def _jobs() -> dict:
    return yaml.safe_load(WORKFLOW.read_text())["jobs"]


def _source_script() -> str:
    (step,) = [s for s in _jobs()["source"]["steps"] if s.get("id") == "source"]
    return step["with"]["script"]


def test_the_source_job_admits_the_workers_app_by_its_exact_login() -> None:
    gate = " ".join(_jobs()["source"]["if"].split())
    assert f"github.event.pull_request.user.login == '{APP}'" in gate, gate
    assert f"pr.user.login === '{APP}'" in _source_script()


def test_trusted_associations_are_kept() -> None:
    gate = _jobs()["source"]["if"]
    script = _source_script()
    for association in ("OWNER", "MEMBER", "COLLABORATOR"):
        assert f"github.event.pull_request.author_association == '{association}'" in gate
        assert f"'{association}'" in script


def test_no_other_bot_and_no_pattern_is_trusted() -> None:
    text = WORKFLOW.read_text()
    assert text.count("[bot]") == text.count(APP), "a bot other than the workers' App is named"
    for pattern in ("endsWith(", "contains(", ".endsWith(", ".includes('[bot]"):
        assert pattern not in _jobs()["source"]["if"] + _source_script(), pattern


def test_only_the_source_job_reads_the_author_and_every_other_job_needs_it() -> None:
    for name, job in _jobs().items():
        if name == "source":
            continue
        assert not any(word in str(job.get("if", "")) for word in GATE_WORDS), name
        needs = job.get("needs")
        assert "source" in ([needs] if isinstance(needs, str) else needs or []), name
        if "always()" in str(job.get("if", "")):
            assert "needs.source.result == 'success'" in job["if"], name
