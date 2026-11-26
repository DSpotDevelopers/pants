# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""How DSpot's Pants build makes the release it publishes.

The build job runs one script from the checked-out source, so a pull request changes how the release is built and
proves it in its own run (`pull_request_target` takes the workflow from the default branch, never the build). The script
links every native file against glibc 2.28, the floor `DSPOT-PATCHES.md` names, and refuses the release when any
native file of its wheel or PEX needs a newer glibc.
"""

from __future__ import annotations

import ast
from pathlib import Path

import yaml

WORKFLOW = Path(".github/workflows/dspot-pants.yaml")
SCRIPT = Path("build-support/bin/dspot_release_build.sh")


def test_the_wheel_receives_the_existing_floor_compiler() -> None:
    script = SCRIPT.read_text()
    assert 'export CC="${wrappers}/cc"' in script
    assert 'export LDSHARED="${wrappers}/cc -shared"' in script
    wheel = next(
        node for node in ast.walk(ast.parse(Path("src/python/pants/BUILD").read_text()))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        and node.func.id == "python_distribution"
    )
    env_vars = ast.literal_eval(next(k.value for k in wheel.keywords if k.arg == "env_vars"))
    assert {"CC", "LDSHARED"} <= set(env_vars)


def _build_steps() -> list[dict]:
    return yaml.safe_load(WORKFLOW.read_text())["jobs"]["build"]["steps"]


def test_the_build_job_builds_the_release_with_the_sources_script() -> None:
    (step,) = [
        s for s in _build_steps() if s.get("name") == "Build the release from the checked source"
    ]
    assert step["run"].strip() == str(SCRIPT), step["run"]
    assert step["env"]["EXPECTED_HEAD"] == "${{ needs.source.outputs.head }}"


def test_the_script_links_natives_against_the_floor_and_checks_the_wheel_and_pex() -> None:
    script = SCRIPT.read_text()
    assert 'readonly GLIBC="2.28"' in script
    assert "-target x86_64-linux-gnu.${GLIBC}" in script
    assert 'CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_LINKER="${wrappers}/cc"' in script
    check = script[script.index("dspot_glibc_floor.py") :]
    assert '--glibc "${GLIBC}"' in check
    assert "pantsbuild_pants-" in check and "dist/src.python.pants/pants-pex.pex" in check


def test_the_wrappers_stay_outside_the_checkout_and_no_cached_engine_is_reused() -> None:
    """The engine hash covers build-support/bin/rust's files, so wrappers written there change the build's hash but not
    the tests job's checkout: the tests job then rebuilds the engine it was handed, without a Rust toolchain. The
    wrappers live in the runner's temp folder instead, and a release clears the bootstrap's native-code cache, so it
    never reuses an engine of the same source linked against the runner's glibc."""
    script = SCRIPT.read_text()
    assert 'wrappers="${RUNNER_TEMP:?' in script
    assert "build-support/bin/rust/glibc" not in script
    assert 'rm -rf "${HOME}/.cache/pants/native_code"' in script
