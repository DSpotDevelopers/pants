# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""A job-local endpoint whose connections travel over docker exec, not daemon-host ports."""

from __future__ import annotations

import os
import signal
import socket
import socketserver
import subprocess
import threading
from collections.abc import Sequence
from contextlib import AbstractContextManager, suppress


def _kill(child: subprocess.Popen[bytes]) -> None:
    with suppress(ProcessLookupError):
        os.killpg(child.pid, signal.SIGKILL)
    child.wait()


class ExecTunnel(AbstractContextManager["ExecTunnel"]):
    def __init__(self, command: Sequence[str]) -> None:
        self.children: set[subprocess.Popen[bytes]] = set()
        self._clients: set[socket.socket] = set()
        self._lock = threading.Lock()
        self._closing = False
        owner = self

        class Handler(socketserver.BaseRequestHandler):
            def handle(self) -> None:
                with owner._lock:
                    if owner._closing:
                        return
                    child = subprocess.Popen(
                        command,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        start_new_session=True,
                    )
                    owner.children.add(child)
                    owner._clients.add(self.request)
                assert child.stdin is not None and child.stdout is not None

                def upload() -> None:
                    try:
                        while data := self.request.recv(65536):
                            child.stdin.write(data)
                            child.stdin.flush()
                    except (OSError, ValueError):
                        pass
                    finally:
                        try:
                            child.stdin.close()
                        except BrokenPipeError:
                            pass

                writer = threading.Thread(target=upload, daemon=True)
                writer.start()
                try:
                    while data := child.stdout.read1(65536):
                        self.request.sendall(data)
                except OSError:
                    pass
                finally:
                    try:
                        self.request.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    _kill(child)
                    writer.join()
                    child.stdout.close()
                    with owner._lock:
                        owner.children.discard(child)
                        owner._clients.discard(self.request)

        self._server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = False
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def __enter__(self) -> ExecTunnel:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._server.shutdown()
        self._thread.join()
        with self._lock:
            self._closing = True
            clients, children = tuple(self._clients), tuple(self.children)
        for client in clients:
            try:
                client.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        for child in children:
            _kill(child)
        # Wait for handlers' resource cleanup, including the upload threads.
        self._server.server_close()
