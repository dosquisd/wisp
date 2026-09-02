from dataclasses import dataclass, field

from src.config.settings import WispConfig
from src.providers.base import DeployVMResult


@dataclass
class AppState:
    config: WispConfig = field(default_factory=WispConfig)
    provider_name: str = "aws"
    selected_region: str = "us-east-2"
    last_deployment: DeployVMResult | None = None

    def reset_config(self) -> None:
        self.config = WispConfig()
