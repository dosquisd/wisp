"""Tests for `wisp.utils.logger.setup_logger` sink selection.

The logger is a pure function of the environment, so these tests drive it
through `monkeypatch` with unique logger names (the module-level `wisp`
singleton is never touched). The daemon branch must stay filesystem-silent;
the file branch must keep its handler order (rotating first, console second)
and fall back to the platformdirs log dir when `WISP_LOG_DIR` is empty.
"""

import logging
import logging.handlers
from pathlib import Path

from wisp.config.constants import WISP_LOG_DIR
from wisp.utils.logger import setup_logger


def _handler_types(logger: logging.Logger) -> list[type]:
    """Return the logger's handler types in attachment order."""
    return [type(handler) for handler in logger.handlers]


def test_daemon_mode_uses_stderr_only(monkeypatch):
    """With WISP_DAEMON=1 the logger has a single DEBUG stderr handler."""
    monkeypatch.setenv("WISP_DAEMON", "1")
    logger = setup_logger("wisp-test-daemon-stderr")

    assert _handler_types(logger) == [logging.StreamHandler]
    assert logger.handlers[0].level == logging.DEBUG
    assert logger.propagate is False


def test_daemon_mode_creates_nothing_on_disk(monkeypatch, tmp_path):
    """The daemon branch must not create the log directory."""
    monkeypatch.setenv("WISP_DAEMON", "1")
    missing_dir = tmp_path / "log" / "never-created"
    monkeypatch.setenv("WISP_LOG_DIR", str(missing_dir))

    setup_logger("wisp-test-daemon-no-disk")

    assert not missing_dir.exists()


def test_default_mode_keeps_file_and_console_handlers(monkeypatch, tmp_path):
    """Without the marker: [RotatingFileHandler, StreamHandler] at [DEBUG, ERROR]."""
    monkeypatch.delenv("WISP_DAEMON", raising=False)
    monkeypatch.setenv("WISP_LOG_DIR", str(tmp_path))
    logger = setup_logger("wisp-test-default")

    assert _handler_types(logger) == [
        logging.handlers.RotatingFileHandler,
        logging.StreamHandler,
    ]
    assert [handler.level for handler in logger.handlers] == [
        logging.DEBUG,
        logging.ERROR,
    ]
    rotating = logger.handlers[0]
    assert isinstance(rotating, logging.handlers.RotatingFileHandler)
    assert rotating.backupCount == 3


def test_empty_log_dir_override_falls_back_to_default(monkeypatch):
    """R4 regression: WISP_LOG_DIR="" must not resolve the log file to the CWD."""
    monkeypatch.delenv("WISP_DAEMON", raising=False)
    monkeypatch.setenv("WISP_LOG_DIR", "")
    cwd_before = set(Path.cwd().iterdir())

    logger = setup_logger("wisp-test-empty-env")

    rotating = logger.handlers[0]
    assert isinstance(rotating, logging.handlers.RotatingFileHandler)
    assert Path(rotating.baseFilename).parent == Path(WISP_LOG_DIR)
    # Nothing new appeared in the CWD of the test process.
    assert set(Path.cwd().iterdir()) == cwd_before
    assert (Path(WISP_LOG_DIR) / "wisp.log").exists()


def test_propagation_disabled():
    """Every configured logger keeps propagation off to avoid duplicates."""
    assert setup_logger("wisp-test-propagation").propagate is False
