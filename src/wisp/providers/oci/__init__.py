from wisp.providers.oci.constants import (
    DEFAULT_MEMORY_IN_GBS,
    DEFAULT_OCPUS,
    DEFAULT_SHAPE,
)
from wisp.providers.oci.provider import OCIProvider

__all__ = [
    "OCIProvider",
    "DEFAULT_SHAPE",
    "DEFAULT_OCPUS",
    "DEFAULT_MEMORY_IN_GBS",
]
