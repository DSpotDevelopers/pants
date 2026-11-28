# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""Prints the targets qualification runs: the change's selection, or with `--all` every target (the nightly full
run), within the qualified scope.

The scope (dspot_qualification_scope.toml) names the backends the company enables. A target under
src/python/pants/backend/ is in scope when its directory holds code those backends load, with the
backends Pants always loads; Pants itself computes that closure (`dependencies --transitive`). Every
target outside src/python/pants/backend/ is in scope.
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from collections.abc import Callable, Iterable
from pathlib import Path

SCOPE = Path(__file__).with_name("dspot_qualification_scope.toml")
BACKENDS = "src/python/pants/backend/"
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
    roots = [register_module(b) for b in (*ALWAYS_LOADED, *backends)]
    loaded = [*roots, *pants("dependencies", "--transitive", *roots)]
    return {directory(a) for a in loaded if a.startswith(BACKENDS)}


def in_scope(address: str, directories: set[str]) -> bool:
    return not address.startswith(BACKENDS) or directory(address) in directories


def _split(pants: Pants, addresses: Callable[[], list[str]]) -> tuple[list[str], list[str]]:
    directories = scope_directories(pants, scope()["backend_packages"])
    listed = addresses()
    return (
        [a for a in listed if in_scope(a, directories)],
        [a for a in listed if not in_scope(a, directories)],
    )


def selection(pants: Pants, base: str) -> tuple[list[str], list[str]]:
    """The change's selection, split into the qualified targets and those outside the scope."""
    return _split(
        pants, lambda: pants(f"--changed-since={base}", "--changed-dependents=direct", "list")
    )


def whole(pants: Pants) -> tuple[list[str], list[str]]:
    """Every target, split the same way: what the nightly full run tests."""
    return _split(pants, lambda: pants("list", "::"))


def run_pants(*args: str) -> list[str]:
    out = subprocess.run(["./pants", *args], check=True, stdout=subprocess.PIPE, text=True).stdout
    return [line for line in out.splitlines() if line]


def main(argv: list[str]) -> int:
    (base,) = argv
    qualified, outside = whole(run_pants) if base == "--all" else selection(run_pants, base)
    for address in outside:
        print(f"outside the qualified scope: {address}", file=sys.stderr)
    print("\n".join(qualified))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
