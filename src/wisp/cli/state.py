"""In-memory state shared across TUI screens for a single session."""

from dataclasses import dataclass, field

from wisp.config.credentials import (
    AWSCredentials,
    OCICredentials,
    resolve_aws_credentials,
    resolve_oci_credentials,
)
from wisp.config.settings import (
    WispConfig,
    get_default_provider,
    get_default_region_for,
    load_wisp_config,
    reload_toml_config,
)
from wisp.providers.base import DeployVMResult


def _default_region_for_default_provider() -> str:
    """Region configured for the default provider (fallback: ``"us-east-2"``)."""
    return get_default_region_for(get_default_provider()) or "us-east-2"


@dataclass
class AppState:
    """Mutable per-session state held by :class:`~wisp.cli.app.WispApp`.

    Attributes:
        config (WispConfig): The active session configuration (loaded from the
            ``[general]`` TOML section).
        provider_name (str): Selected provider name.
        selected_region (str): Selected deployment region.
        last_deployment (DeployVMResult | None): Result of the most recent
            deployment, if any.
        aws_credentials (AWSCredentials): Resolved AWS credentials.
        oci_credentials (OCICredentials): Resolved OCI credentials.
    """

    config: WispConfig = field(default_factory=load_wisp_config)
    provider_name: str = field(default_factory=get_default_provider)
    selected_region: str = field(default_factory=_default_region_for_default_provider)
    last_deployment: DeployVMResult | None = None
    aws_credentials: AWSCredentials = field(default_factory=resolve_aws_credentials)
    oci_credentials: OCICredentials = field(default_factory=resolve_oci_credentials)

    def reset_config(self) -> None:
        """Reset :attr:`config` to a fresh :class:`WispConfig` from TOML."""
        self.config = load_wisp_config()

    def get_credentials_for_provider(self, provider_name: str):
        """Return resolved credentials for the given provider."""
        if provider_name == "aws":
            return self.aws_credentials
        elif provider_name == "oci":
            return self.oci_credentials
        return None

    def refresh_credentials(self) -> None:
        """Re-resolve credentials from TOML/env (useful after config changes)."""
        reload_toml_config()
        self.aws_credentials = resolve_aws_credentials()
        self.oci_credentials = resolve_oci_credentials()
