import logging
import logging.handlers
import os
from pathlib import Path

from wisp.config.constants import WISP_LOG_DIR, ensure_log_dir

# Configuring the logger creates its log directory (a deliberate side effect of
# setting up file logging); nothing is created in the current working directory.
ensure_log_dir()


def setup_logger(name: str) -> logging.Logger:
    """Configure and return the wisp logger.

    Attaches a rotating file handler at ``<WISP_LOG_DIR>/wisp.log`` (5 MB per file,
    5 backups, level ``DEBUG``) and a stderr handler (level ``ERROR``). Propagation
    is disabled to prevent duplicate records.

    Args:
        name (str): Logger name.

    Returns:
        logging.Logger: The configured logger.
    """
    log_dir = os.getenv("WISP_LOG_DIR", WISP_LOG_DIR)
    if isinstance(log_dir, str):
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

    # Create main logger instance
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Clear any existing handlers to avoid duplicate logs
    logger.handlers.clear()

    # File handler for logging to a file
    file_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(funcName)s] %(message)s"
    )
    rotating_handler = logging.handlers.RotatingFileHandler(
        log_dir / "wisp.log",
        maxBytes=5 * 1024 * 1024,  # 5MB per file
        backupCount=3,  # Keep 5 backup files
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

    # Add handlers to the logger
    logger.addHandler(rotating_handler)
    logger.addHandler(console_handler)

    # Disable propagation to prevent duplicate log messages
    logger.propagate = False

    return logger


logger = setup_logger("wisp")
