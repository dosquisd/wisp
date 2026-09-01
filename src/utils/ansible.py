import os
import sys
from pathlib import Path

ANSIBLE_PLAYBOOK = "ansible-playbook"


def get_ansible_playbook_bin() -> str:
    """Resolve the `ansible-playbook` binary.

    Prefers a system/global install (any `ansible-playbook` found on PATH that
    is not inside the current virtualenv), and falls back to the project
    virtualenv's binary. Raises FileNotFoundError with a clear message if
    neither is available.
    """
    global_bin = _find_global_bin()
    if global_bin:
        return global_bin

    local_bin = _find_local_bin()
    if local_bin:
        return local_bin

    raise FileNotFoundError(
        "ansible-playbook not found. Install it globally, or add 'ansible-core' "
        "as a project dependency and run 'uv sync'."
    )


def _find_global_bin() -> str | None:
    """Search PATH, ignoring candidates that live inside the current venv."""
    venv_prefix = Path(sys.prefix).resolve()
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory).expanduser() / ANSIBLE_PLAYBOOK
        if candidate.is_file() and os.access(candidate, os.X_OK):
            resolved = candidate.resolve()
            if not _is_within(resolved, venv_prefix):
                return str(resolved)
    return None


def _find_local_bin() -> str | None:
    """Look for the binary inside the current virtualenv's bin directory."""
    local_bin = Path(sys.prefix) / "bin" / ANSIBLE_PLAYBOOK
    if local_bin.is_file() and os.access(local_bin, os.X_OK):
        return str(local_bin)
    return None


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
