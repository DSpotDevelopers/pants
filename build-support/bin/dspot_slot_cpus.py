# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""Prints how many processes a CI job may run at once: the CPUs its slot is granted, never the host's.

Inside a runner's container, os.cpu_count() reports the host's CPUs, so Pants' default process parallelism ran
32 test processes on a slot with a 4-vCPU quota. The rule, as dspot-company-data's ci/cpu_budget.py reads a slot:
the smaller of the tightest CPU quota on this process's cgroup and its ancestors (cgroup v2 cpu.max) and the slot's
declared share (RUNNER_VCPU_PER_SLOT, else the runner name's -nprocN-tslotsK-: N over K); with neither, at most 2.
Never more than the CPUs this process may run on.
"""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

SLOT_NAME = re.compile(r"-nproc([0-9]+)-tslots([1-9][0-9]*)(-|$)")
UNKNOWN_SHARE = 2


def whole(value: str) -> int | None:
    value = (value or "").strip()
    return int(value) if value.isdigit() and int(value) >= 1 else None


def quota(cpu_max: str) -> int | None:
    parts = (cpu_max or "").split()
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit() and int(parts[1]) > 0:
        return max(1, int(parts[0]) // int(parts[1]))
    return None


def budget(cpu_maxes: Sequence[str], *, runner: str, per_slot: str, usable: int) -> int:
    quotas = [q for q in map(quota, cpu_maxes) if q]
    named = SLOT_NAME.search(runner or "")
    share = whole(per_slot) or (
        max(1, int(named.group(1)) // int(named.group(2))) if named else None
    )
    bounds = [b for b in (min(quotas) if quotas else None, share) if b]
    return max(1, min(min(bounds) if bounds else UNKNOWN_SHARE, usable))


def main(
    *,
    root: Path = Path("/sys/fs/cgroup"),
    membership: Path = Path("/proc/self/cgroup"),
    environ: Mapping[str, str] = os.environ,
    usable: int | None = None,
) -> int:
    group = next(
        (
            line[3:].strip()
            for line in membership.read_text().splitlines()
            if line.startswith("0::")
        ),
        "/",
    )
    parts = [part for part in group.split("/") if part]
    folders = [root.joinpath(*parts[:n]) for n in range(len(parts), -1, -1)]
    cpu_maxes = [(f / "cpu.max").read_text() for f in folders if (f / "cpu.max").is_file()]
    return budget(
        cpu_maxes,
        runner=environ.get("RUNNER_NAME", ""),
        per_slot=environ.get("RUNNER_VCPU_PER_SLOT", ""),
        usable=usable or len(os.sched_getaffinity(0)),
    )


if __name__ == "__main__":
    print(main())
    sys.exit(0)
