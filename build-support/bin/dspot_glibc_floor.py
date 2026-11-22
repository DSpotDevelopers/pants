# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""Refuse a native file that needs a newer glibc than DSpot's release floor.

A dynamically linked ELF file names each glibc symbol version it needs (`GLIBC_2.2.5`, `GLIBC_2.34`, ...); the
highest one is the oldest glibc that can load it. Each path given is a native file, or a wheel or PEX (a zip)
whose members named in NATIVE are read, at any depth. A path with no native file is refused too, so an empty
archive can never pass. Exit 1 names every file over the floor.
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from collections.abc import Iterator
from pathlib import Path, PurePosixPath

NATIVE = ("native_engine.so", "native_client", "sandboxer", "pants_lock")
VERSION = re.compile(rb"GLIBC_(\d+)\.(\d+)(?:\.(\d+))?")


def highest(data: bytes) -> tuple[int, ...] | None:
    """The highest glibc version `data` names, or None when it names none."""
    found = [tuple(int(part) for part in match.groups() if part is not None) for match in VERSION.finditer(data)]
    return max(found) if found else None


def natives(path: Path) -> Iterator[tuple[str, bytes]]:
    """(name, bytes) of each native file at `path`: the file itself, or an archive's NATIVE members."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            for member in archive.namelist():
                if PurePosixPath(member).name in NATIVE:
                    yield f"{path}!{member}", archive.read(member)
    else:
        yield str(path), path.read_bytes()


def problems(paths: list[Path], floor: tuple[int, ...]) -> list[str]:
    """Each file over `floor`, and each path holding no native file."""
    out = []
    for path in paths:
        found = False
        for name, data in natives(path):
            found = True
            top = highest(data)
            if top is not None and top > floor:
                out.append(f"{name}: needs GLIBC_{'.'.join(map(str, top))}, over GLIBC_{'.'.join(map(str, floor))}")
        if not found:
            out.append(f"{path}: holds no native file ({', '.join(NATIVE)})")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--glibc", required=True, help="the floor, e.g. 2.28")
    parser.add_argument("paths", nargs="+", type=Path)
    options = parser.parse_args(argv)
    floor = tuple(int(part) for part in options.glibc.split("."))
    found = problems(options.paths, floor)
    for problem in found:
        print(problem, file=sys.stderr)
    if not found:
        print(f"every native file needs GLIBC_{options.glibc} at most")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
