from src.wireguard.local_client import (
    connect_wireguard_client,
    disconnect_wireguard_client,
)
from src.wireguard.remote_server import configure_remote_server

__all__ = [
    "configure_remote_server",
    "connect_wireguard_client",
    "disconnect_wireguard_client",
]
