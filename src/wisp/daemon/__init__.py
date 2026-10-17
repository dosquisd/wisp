"""Wisp's privileged local daemon package.

Importing anything from this package (e.g. ``wisp.daemon.server``) marks the
current process as the privileged daemon via the ``WISP_DAEMON`` environment
marker, which ``wisp.utils.logger.setup_logger`` reads to pick the daemon's
logging sink.
"""

import os

# Process-local marker: any import from this package marks the process as the
# privileged daemon. Read by setup_logger() to pick the daemon's sink. Never
# set this machine-wide — user processes must keep their own log file.
os.environ.setdefault("WISP_DAEMON", "1")
