from __future__ import annotations

import logging
from pathlib import Path

from stt_arena.config import Settings
from stt_arena.logging_config import configure_logging


def test_configure_logging_writes_to_log_file(tmp_path: Path) -> None:
    settings = Settings(
        log_dir=str(tmp_path),
        log_file="test.log",
        log_level="INFO",
    )

    log_path = configure_logging(settings)
    logging.getLogger("stt_arena.tests").info("hello from test logger")
    for handler in logging.getLogger().handlers:
        handler.flush()

    assert log_path == tmp_path / "test.log"
    assert "hello from test logger" in log_path.read_text(encoding="utf-8")
