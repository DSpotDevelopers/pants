# Copyright 2026 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from pants.engine.internals.buildbarn_integration_tests import stack as buildbarn


def completed_process(
    args: Sequence[str],
    *,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=args, returncode=returncode, stdout=stdout, stderr=stderr
    )


def test_load_configured_service_image_reads_compose_image_config(tmp_path: Path) -> None:
    image_config = tmp_path / "docker-compose.images.yaml"
    image_config.write_text(
        "services:\n"
        "  storage-image:\n"
        '    profiles: ["image_refs"]\n'
        "    image: ghcr.io/example/storage:tag@sha256:abc123\n",
        encoding="utf-8",
    )

    assert (
        buildbarn._load_configured_service_image(image_config, "storage-image")
        == "ghcr.io/example/storage:tag@sha256:abc123"
    )


def test_prepare_remote_execution_dirs_creates_expected_paths(tmp_path: Path) -> None:
    buildbarn._prepare_remote_execution_dirs(tmp_path)

    expected_paths = [
        tmp_path / "storage-cas" / "persistent_state",
        tmp_path / "storage-ac" / "persistent_state",
        tmp_path / "storage-fsac" / "persistent_state",
        tmp_path / "worker" / "build",
        tmp_path / "worker" / "cache",
        tmp_path / "bb",
    ]
    assert all(path.exists() for path in expected_paths)


def test_write_runtime_overlay_uses_instance_name(tmp_path: Path) -> None:
    overlay_path = tmp_path / "runtime.libsonnet"

    buildbarn._write_runtime_overlay(
        overlay_path,
        instance_name="pants-test",
        execution_image_reference="ghcr.io/example/executor:tag@sha256:" + "e" * 64,
    )

    overlay = overlay_path.read_text(encoding="utf-8")
    assert '"pants-test"' in overlay
    assert "ghcr.io/example/executor:tag@sha256:" in overlay


def test_write_compose_logs_uses_compose_command(tmp_path: Path) -> None:
    commands: list[tuple[tuple[str, ...], bool]] = []

    def run_command(args: Sequence[str], check: bool) -> subprocess.CompletedProcess[str]:
        commands.append((tuple(args), check))
        return completed_process(args, stdout="service log\n")

    stack = buildbarn.LocalBuildbarnStack(temp_dir=tmp_path, run_command=run_command)
    stack._project_name = "pants-buildbarn-test"
    stack._runtime_root = tmp_path
    stack._env_file = tmp_path / "compose.env"
    stack._compose_file = tmp_path / "docker-compose.yaml"
    stack._compose_profiles = ("cache",)
    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)

    buildbarn._write_compose_logs(stack)

    assert (tmp_path / "logs" / "compose.log").read_text(encoding="utf-8") == "service log\n"
    assert commands == [
        (
            (
                "docker",
                "compose",
                "--project-name",
                "pants-buildbarn-test",
                "--file",
                str(tmp_path / "docker-compose.yaml"),
                "--env-file",
                str(tmp_path / "compose.env"),
                "--profile",
                "cache",
                "logs",
                "--no-color",
                "--timestamps",
            ),
            False,
        )
    ]


def test_compose_uses_only_owned_volumes_and_has_no_host_ports() -> None:
    import yaml

    config = yaml.safe_load(buildbarn._CONFIG_ROOT.joinpath("docker-compose.yaml").read_text())
    for service in config["services"].values():
        assert not service.get("ports"), "The daemon host's loopback is not the job's loopback"
        for mount in service.get("volumes", ()):
            source = mount.split(":")[0]
            assert source in config["volumes"], f"Host bind: {mount}"
    assert "relay" in config["services"]
    assert "seed" in config["services"]


@pytest.mark.parametrize("remote", [False, True])
def test_stack_copies_inputs_before_start_and_tunnels_on_its_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, remote: bool
) -> None:
    commands: list[tuple[str, ...]] = []
    tunnels: list[tuple[str, ...]] = []
    closed: list[bool] = []

    def run(args: Sequence[str], check: bool) -> subprocess.CompletedProcess[str]:
        commands.append(tuple(args[args.index("--profile") + 2 :]))
        return completed_process(args)

    class Tunnel:
        port = 27123

        def __init__(self, args: Sequence[str]) -> None:
            tunnels.append(tuple(args))

        def __exit__(self, *args) -> None:
            closed.append(True)

    monkeypatch.setattr(buildbarn, "ExecTunnel", Tunnel)
    monkeypatch.setattr(buildbarn, "_wait_for_tcp_readiness", lambda **kwargs: None)
    stack = buildbarn.LocalBuildbarnStack(temp_dir=tmp_path, run_command=run)
    launched = stack.launch_remote_execution() if remote else stack.launch_cache_only()
    assert launched.address == "grpc://127.0.0.1:27123"  # Job-local relay, no daemon-host listener.
    assert commands[0] == ("create", "seed")
    up = next(i for i, command in enumerate(commands) if command[0] == "up")
    copied = [command for command in commands[:up] if command[0] == "cp"]
    assert {command[-1] for command in copied} == {
        "seed:/config/",
        "seed:/storage-cas/",
        "seed:/storage-ac/",
        *({"seed:/storage-fsac/", "seed:/worker/", "seed:/bb/"} if remote else set()),
    }
    assert (tmp_path / "assets" / "runtime.libsonnet").read_text().startswith("{\n")
    assert tunnels[0][-2:] == (("frontend" if remote else "cache"), "8980")
    assert "relay" in tunnels[0] and "/dev/tcp/$1/$2" in tunnels[0][-4]
    if remote:
        assert ("exec", "-T", "runner", "test", "-S", "/worker/runner") in commands
    assert not any(command[0] == "port" for command in commands)
    stack.teardown()
    assert closed == [True]
    assert commands[-1] == ("down", "-v", "--remove-orphans")
