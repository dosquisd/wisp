import enum

from wisp.providers.aws import AWSProvider
from wisp.providers.base import BaseProvider

__all__ = ["PROVIDERS_MAP", "AWSProvider", "BaseProvider", "ProviderEnum"]


# Add more provider types as needed (e.g., Azure, GCP, etc.)


class ProviderEnum(enum.Enum):
    AWS = "aws"


PROVIDERS_MAP: dict[ProviderEnum, type[BaseProvider]] = {
    ProviderEnum.AWS: AWSProvider,
}
