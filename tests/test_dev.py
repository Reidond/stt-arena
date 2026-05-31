from __future__ import annotations

import subprocess
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

import pytest
from stt_arena_tooling import dev


def test_shutdown_processes_stops_uvicorn_before_vite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stopped: list[subprocess.Popen[bytes]] = []
    uvicorn = cast(subprocess.Popen[bytes], object())
    vite = cast(subprocess.Popen[bytes], object())

    monkeypatch.setattr(dev, "_terminate_process", stopped.append)

    dev._shutdown_processes(uvicorn=uvicorn, vite=vite)

    assert stopped == [uvicorn, vite]


def test_main_starts_children_in_separate_sessions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vite = MagicMock()
    vite.poll.return_value = None
    uvicorn = MagicMock()
    uvicorn.poll.return_value = None
    popen = MagicMock(side_effect=[vite, uvicorn])

    monkeypatch.setattr(dev, "VITE_ASSETS", MagicMock())
    monkeypatch.setattr(
        dev,
        "get_settings",
        lambda: SimpleNamespace(
            host="127.0.0.1",
            port=8000,
            resolved_vite_socket_path="/tmp/stt-arena/vite.sock",
        ),
    )
    monkeypatch.setattr(dev, "release_port", lambda _port: [])
    monkeypatch.setattr(dev.subprocess, "Popen", popen)
    monkeypatch.setattr(dev.signal, "signal", lambda *_args: None)
    monkeypatch.setattr(dev.time, "sleep", MagicMock(side_effect=KeyboardInterrupt))

    with pytest.raises(SystemExit):
        dev.main()

    assert popen.call_count == 2
    assert popen.call_args_list[0].kwargs["start_new_session"] is True
    assert popen.call_args_list[1].kwargs["start_new_session"] is True
