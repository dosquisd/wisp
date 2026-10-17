"""Tests for the single-config settings model."""

from wisp.config import constants, settings
from wisp.config.settings import WispConfig


def test_get_active_config_path_returns_user_config():
    """get_active_config_path returns WISP_USER_CONFIG_PATH."""
    assert settings.get_active_config_path() == settings.WISP_USER_CONFIG_PATH


def test_load_toml_config_reads_user_config(tmp_path, monkeypatch):
    """load_toml_config reads the single user-level wisp.toml."""
    cfg = tmp_path / "wisp.toml"
    cfg.write_text('[general]\ndefault_provider = "oci"\n', encoding="utf-8")
    monkeypatch.setattr(constants, "WISP_USER_CONFIG_PATH", cfg)
    monkeypatch.setattr(settings, "WISP_USER_CONFIG_PATH", cfg)
    # Reset the module cache so this test observes its own file, and cannot
    # leak its config into later tests.
    monkeypatch.setattr(settings, "_cached_config", None)
    try:
        settings.reload_toml_config()
        assert settings.get_default_provider() == "oci"
        assert settings.get_active_config_path() == cfg
    finally:
        settings._cached_config = None


def test_save_session_config_writes_to_user_config(tmp_path, monkeypatch):
    """save_session_config writes to WISP_USER_CONFIG_PATH."""
    cfg = tmp_path / "wisp.toml"
    monkeypatch.setattr(constants, "WISP_USER_CONFIG_PATH", cfg)
    monkeypatch.setattr(settings, "WISP_USER_CONFIG_PATH", cfg)
    monkeypatch.setattr(settings, "_cached_config", None)
    try:
        written = settings.save_session_config(
            WispConfig(), provider_regions={"aws": "us-east-2"}
        )
        assert written == cfg
        assert cfg.is_file()
    finally:
        settings._cached_config = None
