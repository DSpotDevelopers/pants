# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import annotations

import zipfile
from pathlib import Path

from dspot_glibc_floor import main, problems

FLOOR = (2, 28)
OLD = b"\x7fELF...GLIBC_2.2.5\x00GLIBC_2.17\x00GLIBC_2.28\x00GLIBC_PRIVATE\x00"
NEW = b"\x7fELF...GLIBC_2.2.5\x00GLIBC_2.34\x00GLIBC_2.39\x00"


def write(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path


def archive(path: Path, members: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w") as out:
        for name, data in members.items():
            out.writestr(name, data)
    return path


def test_a_native_file_at_the_floor_passes(tmp_path: Path) -> None:
    assert problems([write(tmp_path / "native_client", OLD)], FLOOR) == []


def test_a_native_file_over_the_floor_is_refused_by_name(tmp_path: Path) -> None:
    found = problems([write(tmp_path / "sandboxer", NEW)], FLOOR)
    assert found == [f"{tmp_path / 'sandboxer'}: needs GLIBC_2.39, over GLIBC_2.28"]


def test_a_pex_is_read_through_its_embedded_wheel(tmp_path: Path) -> None:
    deps = ".deps/pantsbuild_pants-2.33.2+dspot.10-cp314-cp314-linux_x86_64.whl/pants"
    pex = archive(tmp_path / "pants.pex", {
        f"{deps}/engine/internals/native_engine.so": NEW,
        f"{deps}/bin/pants_lock": OLD,
        "__main__.py": b"GLIBC_2.99 in prose is not a native file",
    })
    assert problems([pex], FLOOR) == [f"{pex}!{deps}/engine/internals/native_engine.so: needs GLIBC_2.39, over GLIBC_2.28"]


def test_an_archive_with_no_native_file_never_passes(tmp_path: Path) -> None:
    wheel = archive(tmp_path / "empty.whl", {"pants/__init__.py": b""})
    assert problems([wheel], FLOOR) == [f"{wheel}: holds no native file (native_engine.so, native_client, sandboxer, pants_lock)"]


def test_the_command_exits_1_over_the_floor_and_0_at_it(tmp_path: Path) -> None:
    assert main(["--glibc", "2.28", str(write(tmp_path / "native_client", NEW))]) == 1
    assert main(["--glibc", "2.28", str(write(tmp_path / "pants_lock", OLD))]) == 0
