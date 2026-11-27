# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import annotations

import runpy
from pathlib import Path

import pytest
from dspot_relocate_python import relocate


def test_extension_build_paths_follow_the_published_interpreter(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    config = staging / "lib/python3.14/_sysconfigdata__linux_x86_64-linux-gnu.py"
    config.parent.mkdir(parents=True)
    config.write_text(
        "build_time_vars = {'prefix': '/install', 'INCLUDEPY': '/install/include/python3.14', "
        "'CFLAGS': '-I/install/include -O3', 'LIBDIR': '/install/lib', 'SIZEOF_INT': 4, "
        "'INSTALL': '/usr/bin/install -c', 'OTHER': '/installation', 'FLAGS': '-I/install -L/install/lib'}"
    )
    makefile = config.parent / "config-3.14-x86_64-linux-gnu/Makefile"
    makefile.parent.mkdir()
    makefile.write_text("prefix=/install\nLIBDIR=/install/lib\nINSTALL=/usr/bin/install -c\n")
    destination = tmp_path / "published"
    relocate(staging, destination)
    staging.rename(destination)
    values = runpy.run_path(str(destination / config.relative_to(staging)))["build_time_vars"]
    assert values["INCLUDEPY"] == str(destination / "include/python3.14")
    assert values["CFLAGS"] == f"-I{destination}/include -O3"
    assert values["LIBDIR"] == str(destination / "lib")
    assert values["SIZEOF_INT"] == 4
    assert values["INSTALL"] == "/usr/bin/install -c"
    assert values["OTHER"] == "/installation"
    assert values["FLAGS"] == f"-I{destination} -L{destination}/lib"
    assert (destination / makefile.relative_to(staging)).read_text() == (
        f"prefix={destination}\nLIBDIR={destination}/lib\nINSTALL=/usr/bin/install -c\n"
    )
    assert str(staging) not in repr(values)


def test_an_unexpected_archive_configuration_refuses_publication(tmp_path: Path) -> None:
    config = tmp_path / "lib/python3.14/_sysconfigdata__linux_x86_64-linux-gnu.py"
    config.parent.mkdir(parents=True)
    config.write_text("build_time_vars = {'prefix': '/unexpected'}")
    with pytest.raises(ValueError, match="Unexpected standalone Python prefix"):
        relocate(tmp_path, tmp_path / "published")
