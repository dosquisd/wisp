import enum

from src.providers.aws import AWSProvider
from src.providers.base import BaseProvider

__all__ = ["PROVIDERS_MAP", "AWSProvider", "BaseProvider", "ProviderType"]


# Add more provider types as needed (e.g., Azure, GCP, etc.)


class ProviderType(enum.Enum):
    AWS = "aws"


PROVIDERS_MAP: dict[ProviderType, type[BaseProvider]] = {
    ProviderType.AWS: AWSProvider,
}
