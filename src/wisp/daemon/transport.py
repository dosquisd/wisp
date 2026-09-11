import asyncio
import socket
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

from wisp.daemon.adapter import BaseAdapter, get_adapter
from wisp.daemon.protocol import Request, Response
from wisp.utils import PlatformEnum, logger


@runtime_checkable
class ServeTransport(Protocol):
    async def __call__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        adapter: BaseAdapter,
    ) -> None:
        """Handle a single client connection.

        Args:
            reader (asyncio.StreamReader): The stream reader for the client.
            writer (asyncio.StreamWriter): The stream writer for the client.
            adapter (BaseAdapter): The platform-specific adapter to use for connecting.
        """
        ...


class BaseTransport(ABC):
    SOCKET_PATH: str

    def __init__(self):
        self.adapter = get_adapter()

    @abstractmethod
    async def serve(self, handler: ServeTransport) -> None:
        """Start the transport server and serve forever.

        Args:
            handler (ServeTransport): The coroutine to handle each client connection.
        """
        pass

    @abstractmethod
    def send(self, req: Request) -> Response:
        """Send a single request to the daemon and return its response.

        Args:
            req (Request): The command to send.

        Response:
            Response: The daemon's reply.
        """
        pass


class UnixSocketTransport(BaseTransport):
    """Transport implementation using Unix domain sockets."""
    # Unix domain socket the daemon listens on (see packaging/wisp.socket).
    SOCKET_PATH: str = "/run/wisp.sock"


    def __init__(self):
        super().__init__()

    async def serve(self, handler: ServeTransport) -> None:
        """Start the asyncio Unix-socket server and serve forever.

        Under systemd socket activation (``LISTEN_FDS`` set) the listening socket is
        adopted from file descriptor 3; for local development the socket is created
        directly at :data:`~wisp.daemon.protocol.SOCKET_PATH`.
        """

        def handle_client_partial(r, w):
            return handler(r, w, self.adapter)

        # systemd gives us the socket via socket activation (fd 3),
        # but for local development we also support creating it directly.
        if "LISTEN_FDS" in __import__("os").environ:
            server = await asyncio.start_unix_server(
                handle_client_partial, sock=self.__socket_from_systemd()
            )
        else:
            server = await asyncio.start_unix_server(
                handle_client_partial, path=self.SOCKET_PATH
            )

        logger.info("wisp daemon listening")
        async with server:
            await server.serve_forever()

    @staticmethod
    def __socket_from_systemd():
        """Build a socket object from the systemd-provided fd 3 (socket activation)."""
        return socket.fromfd(3, socket.AF_UNIX, socket.SOCK_STREAM)

    def send(self, req: Request) -> Response:
        """Send one request to the daemon socket and read one response.

        Args:
            req (Request): The command to send.

        Returns:
            Response: The daemon's reply.

        Raises:
            PermissionError: If the socket cannot be connected — typically because
                the user is not yet in the ``wisp`` group (requires a re-login).
        """
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            try:
                sock.connect(self.SOCKET_PATH)
            except PermissionError as e:
                raise PermissionError(
                    f"Cannot connect to the wisp daemon socket at {self.SOCKET_PATH}. "
                    "You may need to log out and log back in for your 'wisp' group "
                    "membership to take effect."
                ) from e

            sock.sendall(req.encode())
            raw = sock.makefile().readline().encode()
            return Response.decode(raw)


class WindowsTransport(BaseTransport):
    """Transport implementation for Windows (not implemented yet)."""

    def __init__(self):
        super().__init__()

    async def serve(self, handler: ServeTransport) -> None:
        raise NotImplementedError("Windows transport is not implemented yet.")

    def send(self, req: Request) -> Response:
        raise NotImplementedError("Windows transport is not implemented yet.")


def get_transport() -> BaseTransport:
    platform_enum = PlatformEnum.get_platform()

    match platform_enum:
        case PlatformEnum.LINUX | PlatformEnum.MACOS:
            return UnixSocketTransport()
        case PlatformEnum.WINDOWS:
            return WindowsTransport()
        case _:
            raise NotImplementedError(f"Unsupported platform: {platform_enum}")
