# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

import socket
import sys
from concurrent.futures import ThreadPoolExecutor

from pants.engine.internals.buildbarn_integration_tests.docker_tunnel import ExecTunnel


def test_exec_tunnel_forwards_independent_duplex_streams_and_closes() -> None:
    # Stand in for docker exec with a real streaming child, rather than mocking socket I/O.
    command = [
        sys.executable,
        "-u",
        "-c",
        "import os;\nwhile b := os.read(0, 65536): os.write(1, b)",
    ]
    with ExecTunnel(command) as tunnel:

        def exchange(value: bytes) -> None:
            with socket.create_connection(("127.0.0.1", tunnel.port), timeout=2) as client:
                client.sendall(value)
                received = bytearray()
                while len(received) < len(value):
                    received.extend(client.recv(65536))
                assert received == value

        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(exchange, [b"cache\0" * 20000, b"execution\0" * 20000]))
        # Teardown must terminate a client that hasn't closed its stream.
        client = socket.create_connection(("127.0.0.1", tunnel.port), timeout=2)
        client.sendall(b"still open")
        assert client.recv(100) == b"still open"
    assert client.recv(1) == b""
    client.close()
    assert not tunnel.children
