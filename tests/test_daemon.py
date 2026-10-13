"""Tests for the daemon's client-config validation (socket hardening)."""

import pytest

from wisp.daemon.server import validate_client_config

CLEAN_CLIENT_CONFIG = """[Interface]
PrivateKey = abc123=
Address = 10.66.66.2/32
DNS = 1.1.1.1

[Peer]
PublicKey = def456=
AllowedIPs = 0.0.0.0/0, ::/0
Endpoint = 203.0.113.10:51820
"""


@pytest.mark.parametrize(
    "hook",
    ["PreUp", "PostUp", "PreDown", "PostDown"],
)
def test_rejects_script_hook_directives(hook: str) -> None:
    """wg-quick runs these directives as root: they must never reach disk."""
    content = CLEAN_CLIENT_CONFIG.replace(
        "[Peer]", f"{hook} = touch /tmp/pwned\n\n[Peer]"
    )
    with pytest.raises(ValueError, match="Directive not allowed"):
        validate_client_config(content)


def test_rejects_directive_case_insensitively() -> None:
    content = CLEAN_CLIENT_CONFIG.replace("[Peer]", "postup = evil\n\n[Peer]")
    with pytest.raises(ValueError, match="postup"):
        validate_client_config(content)


def test_rejects_directive_with_leading_whitespace() -> None:
    content = CLEAN_CLIENT_CONFIG.replace("[Peer]", "  PostUp = evil\n\n[Peer]")
    with pytest.raises(ValueError, match="postup"):
        validate_client_config(content)


def test_ignores_directive_names_inside_comments() -> None:
    """A commented mention is prose, not an executable hook."""
    content = CLEAN_CLIENT_CONFIG.replace(
        "[Peer]", "# PostUp = would-be-evil\n\n[Peer]"
    )
    validate_client_config(content)  # does not raise


def test_accepts_clean_client_config() -> None:
    validate_client_config(CLEAN_CLIENT_CONFIG)  # does not raise
