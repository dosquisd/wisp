from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from typing import TypedDict

from src.config.settings import WispConfig

ProgressCallback = Callable[[str, float | None], None]


class DeployVMResult(TypedDict):
    instance_id: str
    public_ip: str
    private_ip: str
    wireguard_port: int


class BaseProvider(ABC):
    @abstractmethod
    def get_available_regions(self) -> Sequence[str]:
        pass

    @abstractmethod
    def deploy_vm(
        self,
        region: str,
        config: WispConfig | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> DeployVMResult:
        pass

    @abstractmethod
    def delete_vm(
        self,
        region: str,
        on_progress: ProgressCallback | None = None,
    ) -> int:
        pass
