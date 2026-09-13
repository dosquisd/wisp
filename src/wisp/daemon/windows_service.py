import asyncio

import servicemanager
import win32service
import win32serviceutil

from wisp.daemon.server import main
from wisp.daemon.transport import WindowsNamedPipeTransport


class WispService(win32serviceutil.ServiceFramework):
    """Windows Service wrapper for the Wisp daemon."""

    _svc_name_ = "WispService"
    _svc_display_name_ = "Wisp Daemon Service"
    _svc_description_ = "Privileged daemon for managing the Wisp VPN on Windows."

    def __init__(self, args):
        super().__init__(args)

        self._loop: asyncio.AbstractEventLoop | None = None
        self._main_task: asyncio.Task | None = None
        self._transport: WindowsNamedPipeTransport | None = None

    def SvcStop(self):
        """Handle a stop request from the Windows Service Control Manager."""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)

        if self._loop is not None and self._transport is not None:
            self._loop.call_soon_threadsafe(self._transport.stop)

    def SvcRun(self):
        """Start and run the Wisp daemon."""
        servicemanager.LogInfoMsg(f"{self._svc_name_} service started.")

        self.ReportServiceStatus(win32service.SERVICE_RUNNING)

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        self._transport = WindowsNamedPipeTransport()

        try:
            self._main_task = self._loop.create_task(main(transport=self._transport))

            self._loop.run_until_complete(self._main_task)

        except Exception as exc:
            servicemanager.LogErrorMsg(f"{self._svc_name_} failed: {exc}")
            raise

        finally:
            self._main_task = None
            self._transport = None

            pending = asyncio.all_tasks(self._loop)

            for task in pending:
                task.cancel()

            if pending:
                self._loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )

            self._loop.close()
            self._loop = None

        servicemanager.LogInfoMsg(f"{self._svc_name_} service stopped.")


if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(WispService)
