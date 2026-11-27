# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import annotations

from pathlib import Path

from dspot_slot_cpus import budget, main


def test_the_slots_quota_bounds_it_never_the_hosts_cpus() -> None:
    # a 4-vCPU quota on a 32-CPU host: the container sees 32, the kernel grants 4
    assert budget(["400000 100000", "max 100000"], runner="", per_slot="", usable=32) == 4
    # the tightest enclosing quota, rounded down, at least 1
    assert (
        budget(["max 100000", "250000 100000", "800000 100000"], runner="", per_slot="", usable=32)
        == 2
    )
    assert budget(["50000 100000"], runner="", per_slot="", usable=32) == 1


def test_the_slots_declared_share_bounds_it_when_it_is_smaller() -> None:
    name = "dspot-ovh-1cbe-nproc16-tslots7-slot1-1795707449"
    assert budget(["max 100000"], runner=name, per_slot="", usable=16) == 2
    assert budget(["max 100000"], runner=name, per_slot="3", usable=16) == 3
    assert budget(["400000 100000"], runner="x-nproc32-tslots2-slot1", per_slot="", usable=32) == 4


def test_a_slot_that_says_nothing_gets_at_most_two() -> None:
    assert budget(["max 100000"], runner="", per_slot="", usable=32) == 2
    assert budget([], runner="", per_slot="", usable=1) == 1


def test_main_reads_this_process_s_own_cgroup_and_its_ancestors(tmp_path: Path) -> None:
    (tmp_path / "slot" / "job").mkdir(parents=True)
    (tmp_path / "cpu.max").write_text("max 100000\n")
    (tmp_path / "slot" / "cpu.max").write_text("400000 100000\n")
    (tmp_path / "slot" / "job" / "cpu.max").write_text("max 100000\n")
    membership = tmp_path / "self.cgroup"
    membership.write_text("0::/slot/job\n")
    assert main(root=tmp_path, membership=membership, environ={}, usable=32) == 4
