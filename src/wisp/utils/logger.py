import logging
import logging.handlers

from wisp.config.constants import ROOTDIR

log_dir = ROOTDIR / "logs"
log_dir.mkdir(parents=True, exist_ok=True)  # Ensure the log directory exists


def setup_logger(name: str) -> logging.Logger:
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
        maxBytes=5 * 1024 * 1024,  # 6MB per file
        backupCount=5,  # Keep 5 backup files
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
