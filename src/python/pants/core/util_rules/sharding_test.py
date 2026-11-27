# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import annotations

import math
import zlib

import pytest

from pants.core.util_rules.sharding import timed_shards


def test_measured_slow_batches_that_collide_in_address_hash_are_separated() -> None:
    timings = {
        "tests:slow-4": 438.62,
        "tests:slow-6": 382.55,
    }
    batches = [(address,) for address in timings]
    assert {zlib.crc32(address.encode()) % 4 for address in timings} == {2}
    assignments = timed_shards(batches, timings, 4)
    loads = [sum(timings[batches[index][0]] for index in shard) for shard in assignments]
    assert max(loads) == 438.62  # The hash puts all 821.17 seconds into one shard.


def test_measured_work_is_balanced_without_splitting_native_batches() -> None:
    batches = [("slow-a",), ("slow-b",), ("fast-a", "fast-b"), ("fast-c",)]
    timings = dict(zip(("slow-a", "slow-b", "fast-a", "fast-b", "fast-c"), (60, 60, 5, 5, 10)))
    shards = timed_shards(batches, timings, 2)
    assert shards == ((0, 2), (1, 3))
    assert sorted(index for shard in shards for index in shard) == list(range(len(batches)))


def test_new_tests_without_history_are_included_conservatively() -> None:
    batches = [("known",), ("new-a", "new-b"), ("new-c",)]
    shards = timed_shards(batches, {"known": 10}, 2)
    assert shards == ((1,), (0, 2))


def test_input_order_does_not_change_batch_ownership() -> None:
    batches = [("a",), ("b",), ("c",), ("d",)]

    def owners(items):
        return tuple(
            tuple(items[index] for index in shard) for shard in timed_shards(items, {"a": 10}, 3)
        )

    assert owners(batches) == owners(list(reversed(batches)))


@pytest.mark.parametrize("value", [-1, math.nan, math.inf, True, "10"])
def test_malformed_history_is_refused(value) -> None:
    with pytest.raises(ValueError, match="finite nonnegative"):
        timed_shards([("a",)], {"a": value}, 2)


def test_empty_shards_and_zero_times_preserve_the_population() -> None:
    assert timed_shards([("a",)], {"a": 0}, 3) == ((0,), (), ())
    assert timed_shards([], {}, 2) == ((), ())


@pytest.mark.parametrize("count", [0, -1, True])
def test_invalid_shard_count_is_refused(count) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        timed_shards([("a",)], {"a": 1}, count)
