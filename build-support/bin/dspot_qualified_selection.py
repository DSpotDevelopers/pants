# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""Prints the targets qualification runs: the change's selection, within the qualified scope.

The scope is the parts of Pants the company uses (dspot_qualification_scope.toml names its backends): the folders holding
code that Pants loads when it runs with those backends, from its entry code and the backends' register modules, plus
those Pants always loads. Pants itself computes that closure (`dependencies --transitive`). A target under
src/python/pants/ is in scope when its folder is in the closure, so a feature none of them loads (Docker environments'
backend, remote execution's Buildbarn tests, the JVM) falls outside by itself. Every target outside src/python/pants/
(the fork's own CI, build-support) is in scope.
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from collections.abc import Callable, Iterable
from pathlib import Path

SCOPE = Path(__file__).with_name("dspot_qualification_scope.toml")
PANTS = "src/python/pants/"
# Pants' entry code, what every run loads before any backend: the module pants_loader.py runs. Never a target of bin's
# folder: pants_loader's depends on `:plugins`, every backend the release PEX ships, and bin's other target holds the
# folder's tests, whose integration helpers reach pants_loader again through pants/__main__.py
ENTRY = "src/python/pants/bin/pants_runner.py"
# The backends every Pants run loads (pants/init/extension_loader.py, load_build_configuration_from_source).
ALWAYS_LOADED = ("pants.core", "pants.backend.project_info")

Pants = Callable[..., list[str]]


def scope() -> dict:
    return tomllib.loads(SCOPE.read_text())


def register_module(backend: str) -> str:
    return f"src/python/{backend.replace('.', '/')}/register.py"


def directory(address: str) -> str:
    # A file address names a file with a suffix; no directory under src/python/pants has a dot.
    path = address.split(":", 1)[0].split("#", 1)[0]
    return path.rsplit("/", 1)[0] if "." in path.rsplit("/", 1)[-1] else path


def scope_directories(pants: Pants, backends: Iterable[str]) -> set[str]:
    roots = [ENTRY, *(register_module(b) for b in (*ALWAYS_LOADED, *backends))]
    loaded = [*roots, *pants("dependencies", "--transitive", *roots)]
    return {directory(a) for a in loaded if a.startswith(PANTS)}


def in_scope(address: str, directories: set[str]) -> bool:
    return not address.startswith(PANTS) or directory(address) in directories


def selection(pants: Pants, base: str) -> tuple[list[str], list[str]]:
    """The change's selection, split into the qualified targets and those outside the scope."""
    directories = scope_directories(pants, scope()["backend_packages"])
    changed = pants(f"--changed-since={base}", "--changed-dependents=direct", "list")
    return (
        [a for a in changed if in_scope(a, directories)],
        [a for a in changed if not in_scope(a, directories)],
    )


def run_pants(*args: str) -> list[str]:
    out = subprocess.run(["./pants", *args], check=True, stdout=subprocess.PIPE, text=True).stdout
    return [line for line in out.splitlines() if line]


def main(argv: list[str]) -> int:
    (base,) = argv
    qualified, outside = selection(run_pants, base)
    for address in outside:
        print(f"outside the qualified scope: {address}", file=sys.stderr)
    print("\n".join(qualified))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
