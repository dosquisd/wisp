"""Tests for path resolution and the absence of import-time side effects."""

import os
import subprocess
import sys
from pathlib import Path


def _run(script: str, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    """Run a Python snippet in a subprocess with an isolated environment.

    Args:
        script (str): Python source passed to ``python -c``.
        cwd (Path): Working directory for the subprocess.
        env (dict[str, str]): Full environment for the subprocess.

    Returns:
        subprocess.CompletedProcess: The finished process (captured output).
    """
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
    )


def _isolated_env(tmp_path: Path) -> dict[str, str]:
    """Build an environment whose Wisp dirs point inside ``tmp_path``.

    Args:
        tmp_path (Path): Base temporary directory for this test.

    Returns:
        dict[str, str]: A copy of ``os.environ`` with the three overrides set.
    """
    env = os.environ.copy()
    env["WISP_DATA_DIR"] = str(tmp_path / "data")
    env["WISP_CONFIG_DIR"] = str(tmp_path / "config")
    env["WISP_LOG_DIR"] = str(tmp_path / "log")
    return env


def test_env_overrides_respected(tmp_path):
    """The three WISP_* env vars override the platformdirs defaults."""
    env = _isolated_env(tmp_path)
    result = _run(
        "from wisp.config import constants; "
        "print(constants.WISP_DATA_DIR); "
        "print(constants.WISP_CONFIG_DIR); "
        "print(constants.WISP_LOG_DIR)",
        tmp_path,
        env,
    )
    assert result.returncode == 0, result.stderr
    data, config, log = result.stdout.splitlines()
    assert data == str(tmp_path / "data")
    assert config == str(tmp_path / "config")
    assert log == str(tmp_path / "log")


def test_artifacts_resolve_under_override_dirs(tmp_path):
    """Key, client conf, user config and session paths follow the overrides."""
    env = _isolated_env(tmp_path)
    result = _run(
        "from wisp.config import constants as c; "
        "print(c.WIREGUARD_KEY_PATH); "
        "print(c.WIREGUARD_CLIENT_CONF_PATH); "
        "print(c.WISP_USER_CONFIG_PATH); "
        "print(c.WISP_ACTIVE_SESSION_PATH); "
        "print(c.WISP_LOG_DIR / 'wisp.log')",
        tmp_path,
        env,
    )
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines[0] == str(tmp_path / "data" / "keys" / "wireguard-key.pem")
    assert lines[1] == str(tmp_path / "data" / "wireguard-confs" / "wg0-client.conf")
    assert lines[2] == str(tmp_path / "config" / "wisp.toml")
    assert lines[3] == str(tmp_path / "config" / "active-session.json")
    assert lines[4] == str(tmp_path / "log" / "wisp.log")


def test_project_config_path_removed(tmp_path):
    """WISP_PROJECT_CONFIG_PATH must no longer exist on the module."""
    env = _isolated_env(tmp_path)
    result = _run(
        "from wisp.config import constants; "
        "print(hasattr(constants, 'WISP_PROJECT_CONFIG_PATH'))",
        tmp_path,
        env,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"


def test_import_creates_nothing_in_cwd(tmp_path):
    """Importing the package must not create anything in the CWD.

    Regression test: the constants module and the logger used to mkdir
    ``keys/``, ``wireguard-confs/``, ``logs/`` and touch a ``wisp.toml``
    relative to the current working directory at import time.
    """
    cwd = tmp_path / "workdir"
    cwd.mkdir()
    env = _isolated_env(tmp_path)
    result = _run(
        "import wisp.config.constants; import wisp.utils.logger",
        cwd,
        env,
    )
    assert result.returncode == 0, result.stderr
    assert list(cwd.iterdir()) == []


def test_import_creates_nothing_in_override_dirs(tmp_path):
    """Importing must also not create anything under the override dirs."""
    env = _isolated_env(tmp_path)
    result = _run(
        "import wisp.config.constants; import wisp.utils.logger",
        tmp_path,
        env,
    )
    assert result.returncode == 0, result.stderr
    # Only the log directory is a documented side effect of configuring a
    # logger; the data/config dirs must stay untouched by a bare import.
    assert not (tmp_path / "data").exists()
    assert not (tmp_path / "config").exists()
