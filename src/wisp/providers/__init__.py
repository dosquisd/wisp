"""Cloud provider registry.

Maps each :class:`ProviderEnum` value to its concrete
:class:`~wisp.providers.base.BaseProvider` implementation via
:data:`PROVIDERS_MAP`.
"""

import enum

from wisp.providers.aws import AWSProvider
from wisp.providers.base import BaseProvider

__all__ = ["PROVIDERS_MAP", "AWSProvider", "BaseProvider", "ProviderEnum"]


# Add more provider types as needed (e.g., Azure, GCP, etc.)


class ProviderEnum(enum.Enum):
    """Supported cloud providers."""

    AWS = "aws"


PROVIDERS_MAP: dict[ProviderEnum, type[BaseProvider]] = {
    ProviderEnum.AWS: AWSProvider,
}
