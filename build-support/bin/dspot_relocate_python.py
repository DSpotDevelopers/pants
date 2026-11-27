# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""Relocate the pinned standalone Python's extension-build metadata before publication."""

from __future__ import annotations

import pprint
import re
import runpy
import sys
from pathlib import Path


def relocate(installation: Path, destination: Path) -> None:
    (config,) = installation.glob("lib/python*/_sysconfigdata_*.py")
    values = runpy.run_path(str(config))["build_time_vars"]
    # This is the build prefix of our checksum-pinned PBS archive, not the staging directory.
    if values["prefix"] != "/install":
        raise ValueError(f"Unexpected standalone Python prefix: {values['prefix']!r}")
    # Match the build prefix as a path, including compiler flags, never the install command.
    prefix = re.compile(r"(^|[\s=,:;'\"()]|-[ILF])/install(?=/|$|[\s,:;'\"()])")

    def rebase(value: str) -> str:
        return prefix.sub(lambda match: match[1] + str(destination), value)

    values = {
        key: rebase(value) if isinstance(value, str) else value for key, value in values.items()
    }
    config.write_text("build_time_vars = " + pprint.pformat(values) + "\n")
    for makefile in installation.glob("lib/python*/config-*/Makefile"):
        makefile.write_text(rebase(makefile.read_text()))


if __name__ == "__main__":
    relocate(Path(sys.argv[1]), Path(sys.argv[2]))
