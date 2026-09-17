"""Cloud provider registry.

Maps each :class:`ProviderEnum` value to its concrete
:class:`~wisp.providers.base.BaseProvider` implementation via
:data:`PROVIDERS_MAP`.
"""

from wisp.providers.aws import AWSProvider
from wisp.providers.base import BaseProvider, ProviderEnum
from wisp.providers.oci import OCIProvider

__all__ = [
    "PROVIDERS_MAP",
    "AWSProvider",
    "OCIProvider",
    "BaseProvider",
    "ProviderEnum",
]


PROVIDERS_MAP: dict[ProviderEnum, type[BaseProvider]] = {
    ProviderEnum.AWS: AWSProvider,
    ProviderEnum.OCI: OCIProvider,
}
