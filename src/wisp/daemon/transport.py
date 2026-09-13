import asyncio
import socket
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

try:
    import pywintypes
    import win32con
    import win32file
    import win32pipe
    import win32security
except ImportError, ModuleNotFoundError:
    # These dependencies are not available on non-Windows platforms
    pass

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


class PipeStreamReader:
    """Minimal asyncio-compatible reader for a Windows Named Pipe."""

    def __init__(self, pipe):
        self._pipe = pipe
        self._buffer = bytearray()

    async def readline(self) -> bytes:
        while b"\n" not in self._buffer:
            data = await asyncio.to_thread(self._read)

            if not data:
                break

            self._buffer.extend(data)

        if b"\n" in self._buffer:
            line, _, remaining = self._buffer.partition(b"\n")
            self._buffer = bytearray(remaining)
            return bytes(line) + b"\n"

        data = bytes(self._buffer)
        self._buffer.clear()
        return data

    def _read(self) -> bytes:
        _, data = win32file.ReadFile(self._pipe, 64 * 1024)
        return data


class PipeStreamWriter:
    """Minimal asyncio-compatible writer for a Windows Named Pipe."""

    def __init__(self, pipe):
        self._pipe = pipe
        self._buffer = bytearray()
        self._closed = False

    def write(self, data: bytes) -> None:
        if self._closed:
            raise RuntimeError("Cannot write to a closed pipe.")

        self._buffer.extend(data)

    async def drain(self) -> None:
        if not self._buffer:
            return

        data = bytes(self._buffer)
        self._buffer.clear()

        await asyncio.to_thread(
            win32file.WriteFile,
            self._pipe,
            data,
        )

    def close(self) -> None:
        if self._closed:
            return

        self._closed = True
        win32file.CloseHandle(self._pipe)


class WindowsNamedPipeTransport(BaseTransport):
    """Transport implementation using a Windows Named Pipe."""

    PIPE_NAME = r"\\.\pipe\wisp"
    WISP_GROUP = "wisp"

    def __init__(self):
        super().__init__()
        self._stopping = False

    @classmethod
    def _create_security_attributes(
        cls,
    ) -> win32security.SECURITY_ATTRIBUTES:
        """Build the security descriptor for the Wisp Named Pipe."""

        dacl = win32security.ACL()

        # LocalSystem: full control.
        system_sid = win32security.CreateWellKnownSid(
            win32security.WinLocalSystemSid,
            None,
        )

        dacl.AddAccessAllowedAce(
            win32security.ACL_REVISION,
            win32con.GENERIC_ALL,
            system_sid,
        )

        # Built-in Administrators: full control.
        administrators_sid = win32security.CreateWellKnownSid(
            win32security.WinBuiltinAdministratorsSid,
            None,
        )

        dacl.AddAccessAllowedAce(
            win32security.ACL_REVISION,
            win32con.GENERIC_ALL,
            administrators_sid,
        )

        # Wisp group: read/write only.
        wisp_sid, _, _ = win32security.LookupAccountName(
            None,
            cls.WISP_GROUP,
        )

        dacl.AddAccessAllowedAce(
            win32security.ACL_REVISION,
            win32con.GENERIC_READ | win32con.GENERIC_WRITE,
            wisp_sid,
        )

        security_descriptor = win32security.SECURITY_DESCRIPTOR()
        security_descriptor.SetSecurityDescriptorDacl(
            1,
            dacl,
            0,
        )

        security_attributes = win32security.SECURITY_ATTRIBUTES()
        security_attributes.SECURITY_DESCRIPTOR = security_descriptor

        return security_attributes

    @classmethod
    def _create_pipe(cls):
        security_attributes = cls._create_security_attributes()

        return win32pipe.CreateNamedPipe(
            cls.PIPE_NAME,
            win32pipe.PIPE_ACCESS_DUPLEX,
            win32pipe.PIPE_TYPE_BYTE
            | win32pipe.PIPE_READMODE_BYTE
            | win32pipe.PIPE_WAIT,
            win32pipe.PIPE_UNLIMITED_INSTANCES,
            64 * 1024,
            64 * 1024,
            0,
            security_attributes,
        )

    @staticmethod
    def _connect(pipe) -> None:
        try:
            win32pipe.ConnectNamedPipe(pipe, None)
        except pywintypes.error as exc:
            # ERROR_PIPE_CONNECTED: client connected between
            # CreateNamedPipe() and ConnectNamedPipe().
            if exc.winerror != 535:
                raise

    def stop(self) -> None:
        """Stop the server and wake a pending ConnectNamedPipe call."""
        self._stopping = True

        try:
            pipe = win32file.CreateFile(
                self.PIPE_NAME,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0,
                None,
                win32file.OPEN_EXISTING,
                0,
                None,
            )
        except pywintypes.error:
            return

        win32file.CloseHandle(pipe)

    async def serve(self, handler: ServeTransport) -> None:
        logger.info(f"wisp daemon listening on {self.PIPE_NAME}")

        while not self._stopping:
            pipe = await asyncio.to_thread(self._create_pipe)

            try:
                await asyncio.to_thread(self._connect, pipe)

                if self._stopping:
                    break

                reader = PipeStreamReader(pipe)
                writer = PipeStreamWriter(pipe)

                try:
                    await handler(
                        reader,
                        writer,
                        self.adapter,
                    )
                finally:
                    writer.close()

            except pywintypes.error as exc:
                if not self._stopping:
                    logger.error(f"[daemon] Named Pipe error: {exc}")

            finally:
                try:
                    win32file.CloseHandle(pipe)
                except pywintypes.error:
                    pass

        logger.info("wisp daemon stopped")

    def send(self, req: Request) -> Response:
        pipe = win32file.CreateFile(
            self.PIPE_NAME,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            0,
            None,
            win32file.OPEN_EXISTING,
            0,
            None,
        )

        try:
            win32file.WriteFile(
                pipe,
                req.encode(),
            )

            _, data = win32file.ReadFile(
                pipe,
                64 * 1024,
            )

            return Response.decode(data)

        finally:
            win32file.CloseHandle(pipe)


def get_transport() -> BaseTransport:
    platform_enum = PlatformEnum.get_platform()

    match platform_enum:
        case PlatformEnum.LINUX | PlatformEnum.MACOS:
            return UnixSocketTransport()
        case PlatformEnum.WINDOWS:
            # These dependencies are not available on non-Windows platforms, so we import them here.

            return WindowsNamedPipeTransport()
        case _:
            raise NotImplementedError(f"Unsupported platform: {platform_enum}")
