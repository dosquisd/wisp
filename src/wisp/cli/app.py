"""Root Textual application and global styles for the Wisp TUI."""

from textual.app import App
from textual.binding import Binding

from wisp.cli.screens import ConfigScreen, DeployScreen, MainMenuScreen
from wisp.cli.screens.shutdown import request_shutdown
from wisp.cli.state import AppState
from wisp.session import (
    find_orphaned_session,
    install_signal_handlers,
    register_atexit,
)


class WispApp(App):
    """The Wisp terminal UI application.

    Owns the shared :class:`~wisp.cli.state.AppState`, defines global CSS and
    key bindings, and installs the main-menu, config, and deploy screens on
    mount.
    """

    TITLE = "Wisp"
    SUB_TITLE = "Ephemeral WireGuard VPNs on your own cloud"

    BINDINGS = [
        Binding("q", "quit", "Salir", show=True),
        Binding("ctrl+c", "quit", "Salir", show=False),
    ]

    CSS = """
    Screen {
        background: #0b0f19;
        color: #f1f5f9;
        align: center middle;
    }

    Header {
        background: #111827;
        color: #38bdf8;
        dock: top;
        height: 1;
    }

    Footer {
        background: #111827;
        dock: bottom;
        height: 1;
    }

    .card {
        background: #1e293b;
        border: round #38bdf8;
        padding: 1 2;
        width: 74;
        height: auto;
        /* Must stay at 100%: any smaller percentage truncates the auto height
           by a row or two, and `overflow-y: auto` then renders a scrollbar for
           that gap alone -- a scroll that reveals nothing but padding. At 100%
           the bar disappears once the content fits and still appears when the
           terminal is genuinely too short to show everything. */
        max-height: 100%;
        overflow-y: auto;
    }

    .title {
        text-style: bold;
        color: #38bdf8;
        text-align: center;
        margin-bottom: 1;
    }

    .subtitle {
        color: #94a3b8;
        text-align: center;
        margin-bottom: 1;
    }

    .btn-primary {
        background: #0284c7;
        color: #ffffff;
        border: none;
        width: 100%;
        margin-top: 1;
    }

    .btn-primary:hover {
        background: #0369a1;
    }

    .btn-secondary {
        background: #334155;
        color: #f8fafc;
        border: none;
        width: 100%;
        margin-top: 1;
    }

    .btn-secondary:hover {
        background: #475569;
    }

    .btn-danger {
        background: #dc2626;
        color: #ffffff;
        border: none;
        width: 100%;
        margin-top: 1;
    }

    .btn-danger:hover {
        background: #b91c1c;
    }

    Input:focus, Select:focus, Switch:focus {
        border: tall #38bdf8;
    }

    Button:focus {
        text-style: bold reverse;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.state = AppState()

    def on_mount(self) -> None:
        """Install the app screens and show the main menu."""
        try:
            from wisp.config.settings import describe_config_sources
            from wisp.utils import logger

            logger.info(describe_config_sources())
        except Exception:
            pass  # purely informational; never block startup over this

        self._configure_shutdown()

        self.install_screen(MainMenuScreen(), name="main_menu")
        self.install_screen(ConfigScreen(), name="config")
        self.install_screen(DeployScreen(), name="deploy")
        self.push_screen("main_menu")
        self._offer_orphan_cleanup()

    def thread_safe_call(self, message: str) -> None:
        """Show a one-line status on whichever screen is active, from any thread.

        Teardown runs on a worker thread long after the screen that started it was
        swapped out, so it cannot hold a reference to it. Resolving the widget at
        call time keeps the teardown tied to the app instead.

        Args:
            message (str): Status text to display.
        """
        if self._exit:
            return
        for widget_id in ("#shutdown-status", "#tunnel-health", "#progress-status-msg"):
            for screen in self.screen_stack:
                try:
                    widget = screen.query_one(widget_id)
                except Exception:
                    continue
                self.call_from_thread(widget.update, message)
                return

    def _configure_shutdown(self) -> None:
        """Wire every shutdown trigger into the session guard.

        Ctrl+C is deliberately *not* routed through a signal handler: Textual's
        driver clears the terminal's ``ISIG`` flag, so Ctrl+C arrives as a key
        event and lands on the ``ctrl+c`` binding below. Keeping it a key event
        means the teardown runs through the same UI path as ``q``, with visible
        progress, instead of interrupting the event loop from a signal context.

        Signals sent from outside (a shell ``kill``, a supervisor, a closing
        terminal) still have to be caught, so ``SIGINT``/``SIGTERM`` go to the
        guard, and ``atexit`` covers normal interpreter exit on all platforms.
        """
        install_signal_handlers(self.state.session_guard)
        register_atexit(self.state.session_guard)

    def action_quit(self) -> None:
        """Tear down any active session, then exit.

        Reached by both ``q`` and ``Ctrl+C`` from every screen.
        """
        request_shutdown(self, "quit requested")

    def _offer_orphan_cleanup(self) -> None:
        """Offer to clean up a session left behind by a previous run.

        A crash, a ``kill -9`` or a power loss leave the marker file on disk.
        Its owning process is gone, so its VM is still running and still
        billing; this surfaces that instead of leaking it silently.
        """
        orphan = find_orphaned_session()
        if orphan is None:
            return

        from wisp.utils import logger

        logger.warning(
            f"Found a session left behind by a dead process: {orphan.summary()}"
        )
        try:
            self.notify(
                f"Se encontró un túnel huérfano de {orphan.summary()}.\n"
                "Sus recursos siguen facturando: límpialos con la opción "
                "4 del menú principal.",
                title="Sesión huérfana",
                severity="warning",
                timeout=15,
            )
        except Exception:
            # Notifications are cosmetic; never let them block startup.
            pass

        # The notification alone expires, so the menu also carries a durable
        # row for this: the warning is only useful while it can still be acted
        # on, and the marker outlives the process that would have used it.
        self.call_after_refresh(self._refresh_menu_orphan_row)

    def _refresh_menu_orphan_row(self) -> None:
        """Ask the main menu to re-evaluate its orphan-cleanup row."""
        try:
            menu = self.get_screen("main_menu")
        except Exception:
            return
        refresher = getattr(menu, "refresh_orphan_row", None)
        if callable(refresher):
            refresher()
