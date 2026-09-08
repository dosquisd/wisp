"""Privileged local daemon that controls the client-side WireGuard interface.

Runs as root under systemd (``wisp.service``, socket-activated by
``wisp.socket``). The unprivileged CLI/TUI talks to it over the Unix socket at
:data:`~wisp.daemon.protocol.SOCKET_PATH`, so it never needs ``sudo`` to bring
the local tunnel up or down.
"""

import asyncio
import subprocess
from pathlib import Path

from wisp.daemon.protocol import SOCKET_PATH, ActionEnum, Request, Response
from wisp.utils.logger import logger

# Local WireGuard config the daemon writes and manages.
WG_CONF_PATH = Path("/etc/wireguard/wg0.conf")


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    """Run a command, raising on non-zero exit, capturing text output."""
    logger.debug(f"[daemon] running: {' '.join(cmd)}")
    return subprocess.run(cmd, check=True, text=True, capture_output=True)


async def handle_connect(config_content: str) -> Response:
    """Write the WireGuard config and bring the ``wg0`` interface up.

    Writes ``config_content`` to :data:`WG_CONF_PATH` with mode ``0600`` and runs
    ``wg-quick up wg0``.

    Args:
        config_content (str): The full WireGuard client configuration.

    Returns:
        Response: ``ok=True`` on success, otherwise the command's stderr.
    """
    try:
        WG_CONF_PATH.parent.mkdir(parents=True, exist_ok=True)
        WG_CONF_PATH.write_text(config_content)
        WG_CONF_PATH.chmod(0o600)
        _run(["wg-quick", "up", "wg0"])
        return Response(ok=True, message="connected")
    except subprocess.CalledProcessError as e:
        return Response(ok=False, message=e.stderr or str(e))


async def handle_disconnect() -> Response:
    """Bring the ``wg0`` interface down via ``wg-quick down wg0``."""
    try:
        _run(["wg-quick", "down", "wg0"])
        return Response(ok=True, message="disconnected")
    except subprocess.CalledProcessError as e:
        return Response(ok=False, message=e.stderr or str(e))


async def handle_status() -> Response:
    """Return the output of ``wg show wg0`` (``ok`` reflects the exit code)."""
    result = subprocess.run(["wg", "show", "wg0"], capture_output=True, text=True)
    return Response(ok=result.returncode == 0, message=result.stdout)


async def handle_client(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    """Serve a single client connection: read one request, reply with one response.

    Reads a newline-delimited :class:`Request`, dispatches to the matching
    handler, and writes back a :class:`Response`. Unknown actions and unexpected
    exceptions produce an ``ok=False`` response.
    """
    try:
        raw = await reader.readline()
        req = Request.decode(raw)

        if req.action == ActionEnum.CONNECT:
            resp = await handle_connect(req.config_content or "")
        elif req.action == ActionEnum.DISCONNECT:
            resp = await handle_disconnect()
        elif req.action == ActionEnum.STATUS:
            resp = await handle_status()
        else:
            resp = Response(ok=False, message=f"unknown action: {req.action}")
    except Exception as e:
        logger.error(f"[daemon] error handling client: {e}")
        resp = Response(ok=False, message=f"internal daemon error: {e}")

    try:
        writer.write(resp.encode())
        await writer.drain()
    finally:
        writer.close()


async def main() -> None:
    """Start the asyncio Unix-socket server and serve forever.

    Under systemd socket activation (``LISTEN_FDS`` set) the listening socket is
    adopted from file descriptor 3; for local development the socket is created
    directly at :data:`~wisp.daemon.protocol.SOCKET_PATH`.
    """
    # systemd gives us the socket via socket activation (fd 3),
    # but for local development we also support creating it directly.
    if "LISTEN_FDS" in __import__("os").environ:
        server = await asyncio.start_unix_server(
            handle_client, sock=_socket_from_systemd()
        )
    else:
        server = await asyncio.start_unix_server(handle_client, path=SOCKET_PATH)

    logger.info("wisp daemon listening")
    async with server:
        await server.serve_forever()


def _socket_from_systemd():
    """Build a socket object from the systemd-provided fd 3 (socket activation)."""
    import socket

    return socket.fromfd(3, socket.AF_UNIX, socket.SOCK_STREAM)


if __name__ == "__main__":
    asyncio.run(main())
