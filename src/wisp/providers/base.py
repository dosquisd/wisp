"""Cloud provider abstraction.

Concrete providers implement :class:`BaseProvider`; the mapping from a provider
name to its class lives in :data:`wisp.providers.PROVIDERS_MAP`.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from typing import TypedDict

from wisp.config.settings import WispConfig

# Progress reporting callback: (message, fraction in [0, 1] or None).
ProgressCallback = Callable[[str, float | None], None]


class DeployVMResult(TypedDict):
    """Summary of a successful deployment returned to the caller."""

    instance_id: str
    public_ip: str
    private_ip: str
    wireguard_port: int


class BaseProvider(ABC):
    """Interface every cloud provider must implement."""

    @abstractmethod
    def get_available_regions(self) -> Sequence[str]:
        """Return the regions available for this provider."""
        pass

    @abstractmethod
    def deploy_vm(
        self,
        region: str,
        force_current_ip: bool = False,
        config: WispConfig | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> DeployVMResult:
        """Provision a VM, configure WireGuard, and connect the local client.

        Args:
            region (str): Target region.
            force_current_ip (bool): Restrict access to the caller's current
                public IP (``/32``).
            config (WispConfig | None): Session config; a default is created if
                ``None``.
            on_progress (ProgressCallback | None): Optional progress callback for
                the TUI.

        Returns:
            DeployVMResult: Details of the deployed VM.
        """
        pass

    @abstractmethod
    def delete_vm(
        self,
        region: str,
        on_progress: ProgressCallback | None = None,
    ) -> int:
        """Disconnect the client, destroy the stack, and clean up local files.

        Args:
            region (str): Region whose stack should be destroyed.
            on_progress (ProgressCallback | None): Optional progress callback.

        Returns:
            int: Number of deleted resources.
        """
        pass
