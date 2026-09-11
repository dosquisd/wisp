"""Privileged local daemon that controls the client-side WireGuard interface.

Runs as root under systemd (``wisp.service``, socket-activated by
``wisp.socket``). The unprivileged CLI/TUI talks to it over the Unix socket at
:data:`~wisp.daemon.protocol.SOCKET_PATH`, so it never needs ``sudo`` to bring
the local tunnel up or down.
"""

import asyncio
import subprocess

from wisp.daemon.adapter import BaseAdapter
from wisp.daemon.protocol import ActionEnum, Request, Response
from wisp.daemon.transport import get_transport
from wisp.utils.logger import logger


async def handle_connect(config_content: str, adapter: BaseAdapter) -> Response:
    """Write the WireGuard config and bring the ``wg0`` interface up.

    Writes ``config_content`` to :data:`WG_CONF_PATH` with mode ``0600`` and runs
    ``wg-quick up wg0``.

    Args:
        config_content (str): The full WireGuard client configuration.
        adapter (BaseAdapter): The platform-specific adapter to use for connecting.

    Returns:
        Response: ``ok=True`` on success, otherwise the command's stderr.
    """
    try:
        adapter.connect(config_content)
        return Response(ok=True, message="connected")
    except subprocess.CalledProcessError as e:
        return Response(ok=False, message=e.stderr or str(e))


async def handle_disconnect(adapter: BaseAdapter) -> Response:
    """Bring the ``wg0`` interface down via ``wg-quick down wg0``."""
    try:
        adapter.disconnect()
        return Response(ok=True, message="disconnected")
    except subprocess.CalledProcessError as e:
        return Response(ok=False, message=e.stderr or str(e))


async def handle_status(adapter: BaseAdapter) -> Response:
    """Return the output of ``wg show wg0`` (``ok`` reflects the exit code)."""
    result = adapter.status()
    return Response(ok=result.returncode == 0, message=result.stdout)


async def handle_client(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter, adapter: BaseAdapter
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
            resp = await handle_connect(req.config_content or "", adapter)
        elif req.action == ActionEnum.DISCONNECT:
            resp = await handle_disconnect(adapter)
        elif req.action == ActionEnum.STATUS:
            resp = await handle_status(adapter)
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
    transport = get_transport()
    await transport.serve(handle_client)


if __name__ == "__main__":
    asyncio.run(main())
