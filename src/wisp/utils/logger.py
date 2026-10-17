import logging
import logging.handlers
import os
import sys
from pathlib import Path

from wisp.config.constants import WISP_LOG_DIR


def setup_logger(name: str) -> logging.Logger:
    """Configure and return a wisp logger, picking the sink by process type.

    Two sink layouts:

    - **Daemon mode** (``WISP_DAEMON=1`` and not Windows): a single stderr
      ``StreamHandler`` at ``DEBUG``. Under systemd, journald captures the
      service's stderr, so journald is the log sink (query with
      ``journalctl -u wisp.service``). Python ``logging`` is thread-safe but
      not process-safe, and the root daemon must not rotate a file other
      processes could clash with; it also touches no directories.
    - **User processes** (TUI/CLI, and the Windows daemon whose service
      wrapper sets ``WISP_LOG_DIR`` process-locally): a rotating file handler
      at ``<WISP_LOG_DIR>/wisp.log`` (5 MB per file, 3 backups, level
      ``DEBUG``) plus a stderr handler (level ``ERROR``), added in that order
      so handler index ``1`` is always the console handler (``main.py``
      raises it to the requested ``--log-level``). Propagation is disabled to
      prevent duplicate records.

    The log directory resolves from ``WISP_LOG_DIR`` with a truthiness guard
    (an empty string falls back to the platformdirs default instead of the
    current working directory) and is created on demand — but only in the
    file branch.

    Args:
        name (str): Logger name.

    Returns:
        logging.Logger: The configured logger.
    """
    # Create main logger instance
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Clear any existing handlers to avoid duplicate logs
    logger.handlers.clear()

    if os.environ.get("WISP_DAEMON") == "1" and sys.platform != "win32":
        # Linux daemon (root, under systemd): journald already captures the
        # service's stderr, and it is the multi-writer-safe sink — Python
        # logging is not process-safe, so a root daemon must not rotate a
        # file. Logging here must also have zero filesystem side effects, so
        # no directory creation at all.
        console_formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(funcName)s] %(message)s"
        )
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(console_formatter)

        logger.addHandler(console_handler)
        logger.propagate = False
        return logger

    # File branch (user processes, and the Windows daemon whose service
    # wrapper points WISP_LOG_DIR at the install's log dir process-locally).
    # Truthiness guard: os.environ.get returns "" when the variable is set
    # but empty, and Path("") resolves to the CWD — fall back to the
    # platformdirs default instead.
    env_dir = os.environ.get("WISP_LOG_DIR")
    log_dir = Path(env_dir) if env_dir else WISP_LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)

    # File handler for logging to a file
    file_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(funcName)s] %(message)s"
    )
    rotating_handler = logging.handlers.RotatingFileHandler(
        log_dir / "wisp.log",
        maxBytes=5 * 1024 * 1024,  # 5MB per file
        backupCount=3,  # Keep 3 backup files
        encoding="utf-8",
    )
    rotating_handler.setLevel(logging.DEBUG)
    rotating_handler.setFormatter(file_formatter)

    # Console handler for logging to the console
    # it's not necessary, because we're using this program behind a TUI, but it's useful for debugging
    console_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(funcName)s] %(message)s"
    )
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)
    console_handler.setFormatter(console_formatter)

    # Add handlers to the logger (rotating first, console second — main.py
    # relies on handler index 1 being the console handler)
    logger.addHandler(rotating_handler)
    logger.addHandler(console_handler)

    # Disable propagation to prevent duplicate log messages
    logger.propagate = False

    return logger


logger = setup_logger("wisp")
