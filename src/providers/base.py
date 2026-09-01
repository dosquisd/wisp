from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import TypedDict


class DeployVMResult(TypedDict):
    instance_id: str
    public_ip: str
    private_ip: str


class BaseProvider(ABC):
    @abstractmethod
    def get_available_regions(self) -> Sequence[str]:
        pass

    @abstractmethod
    def deploy_vm(self, region: str) -> DeployVMResult:
        pass

    @abstractmethod
    def delete_vm(self, region: str) -> int:
        pass
