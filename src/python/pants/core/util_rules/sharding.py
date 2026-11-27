# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import annotations

import heapq
import math
from collections.abc import Mapping, Sequence


def timed_shards(
    batches: Sequence[tuple[str, ...]], timings: Mapping[str, float], count: int
) -> tuple[tuple[int, ...], ...]:
    """Assign whole native batches, longest estimated processing time first.

    Timings are seconds per address, shared equally when collected from a batch.
    New addresses use the largest observed address time (one second for empty
    history). Historical addresses absent from this invocation select nothing.
    The graph and backend partitioners remain the only source of test membership.
    """
    if type(count) is not int or count < 1:
        raise ValueError("The shard count must be a positive integer")
    if any(
        type(value) not in (int, float) or not math.isfinite(value) or value < 0
        for value in timings.values()
    ):
        raise ValueError("Test timings must be finite nonnegative seconds")
    unknown = max((float(value) for value in timings.values()), default=1.0) or 1.0
    weights = [sum(timings.get(address, unknown) for address in batch) for batch in batches]
    # A file's discovery order cannot change ownership. Index only distinguishes
    # identical-address batches supplied by a backend's separate partitions.
    ordered = sorted(range(len(batches)), key=lambda i: (-weights[i], batches[i], i))
    loads = [(0.0, 0, shard) for shard in range(count)]
    heapq.heapify(loads)
    assigned: list[list[int]] = [[] for _ in range(count)]
    for index in ordered:
        load, population, shard = heapq.heappop(loads)
        assigned[shard].append(index)
        heapq.heappush(loads, (load + weights[index], population + 1, shard))
    return tuple(tuple(indices) for indices in assigned)
