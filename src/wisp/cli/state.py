"""In-memory state shared across TUI screens for a single session."""

from dataclasses import dataclass, field

from wisp.config.settings import WispConfig
from wisp.providers.base import DeployVMResult


@dataclass
class AppState:
    """Mutable per-session state held by :class:`~wisp.cli.app.WispApp`.

    Attributes:
        config (WispConfig): The active session configuration.
        provider_name (str): Selected provider name.
        selected_region (str): Selected deployment region.
        last_deployment (DeployVMResult | None): Result of the most recent
            deployment, if any.
    """

    config: WispConfig = field(default_factory=WispConfig)
    provider_name: str = "aws"
    selected_region: str = "us-east-2"
    last_deployment: DeployVMResult | None = None

    def reset_config(self) -> None:
        """Reset :attr:`config` to a fresh :class:`WispConfig` with defaults."""
        self.config = WispConfig()
