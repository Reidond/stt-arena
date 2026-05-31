from __future__ import annotations

import signal
import subprocess

import pytest
from stt_arena_tooling import port_util


def test_listening_pids_parses_lsof_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(port_util.shutil, "which", lambda _name: "/usr/sbin/lsof")

    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="123\nnot-a-pid\n456\n",
        )

    monkeypatch.setattr(port_util.subprocess, "run", fake_run)

    assert port_util._listening_pids(8000) == [123, 456]


def test_release_port_terminates_listener(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0
    killed: list[tuple[int, signal.Signals]] = []

    def fake_listening_pids(_port: int) -> list[int]:
        nonlocal calls
        calls += 1
        return [123] if calls == 1 else []

    monkeypatch.setattr(port_util, "_listening_pids", fake_listening_pids)
    monkeypatch.setattr(port_util.os, "getpid", lambda: 999)
    monkeypatch.setattr(
        port_util,
        "_kill",
        lambda pid, sig: killed.append((pid, sig)),
    )

    assert port_util.release_port(8000) == [123]
    assert killed == [(123, signal.SIGTERM)]
