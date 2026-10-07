"""Active tunnel screen: the persistent view shown while a VPN is up.

Mirrors how a tunnel tool keeps a live view for as long as the tunnel exists,
instead of a one-shot result screen that scrolls away. It shows what the
session is (provider, region, endpoints), how long it has been up, and whether
the local interface is still healthy.

This screen is a terminal state, not a stop on the way somewhere else: the VPN
is ephemeral by design, so every way out of it destroys the tunnel and its cloud
resources. ``q``, ``Ctrl+C``, ``esc``, ``d`` and the button all release the
session through :class:`~wisp.session.SessionGuard`, and closing the terminal
does too via ``SIGHUP``. There is deliberately no "go back and leave it running"
path -- a tunnel nobody is watching is a VM nobody tears down.

While this screen is up, the session guard is armed, so any shutdown trigger,
however it arrives, releases the resources.
"""

import time

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import CenterMiddle, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Static

from wisp.cli.screens.base import WispScreen
from wisp.cli.screens.modal import ConfirmDestroyScreen
from wisp.cli.screens.shutdown import request_shutdown
from wisp.config.settings import save_session_config
from wisp.providers.base import get_provider_display_name
from wisp.session import read_active_session
from wisp.utils import logger


class TunnelScreen(WispScreen):
    """Live view of the running tunnel, with its lifetime on screen."""

    BINDINGS = [
        Binding("escape", "destroy", "Destruir", show=True),
        Binding("d", "destroy", "Destruir", show=False),
    ]

    CSS = """
    #tunnel-title {
        text-align: center;
        margin-bottom: 0;
    }

    #tunnel-subtitle {
        text-align: center;
        margin-bottom: 0;
    }

    #tunnel-panel {
        height: auto;
        border: round #10b981;
        padding: 1 2;
        margin-top: 1;
        margin-bottom: 0;
    }

    #tunnel-panel .row {
        height: auto;
    }

    #tunnel-panel .label {
        width: 20;
        color: #94a3b8;
    }

    #tunnel-panel .value {
        width: 1fr;
    }

    #tunnel-health {
        text-align: center;
        margin-top: 0;
        margin-bottom: 0;
        height: auto;
    }

    #tunnel-note {
        text-align: center;
        color: #64748b;
        margin-top: 0;
    }

    #tunnel-buttons {
        height: 3;
        margin-top: 1;
    }

    #tunnel-buttons Button {
        width: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with CenterMiddle():
            with Vertical(classes="card"):
                yield Static(
                    "[bold green]Túnel Activo[/bold green]",
                    id="tunnel-title",
                    classes="title",
                )
                yield Static(
                    "El túnel permanece establecido mientras Wisp siga abierto.",
                    id="tunnel-subtitle",
                    classes="subtitle",
                )
                with Vertical(id="tunnel-panel"):
                    yield Static("", id="tunnel-session", classes="row")
                    yield Static("", id="tunnel-endpoint", classes="row")
                    yield Static("", id="tunnel-instance", classes="row")
                    yield Static("", id="tunnel-uptime", classes="row")
                yield Static("", id="tunnel-health")
                yield Static(
                    "q / Ctrl+C / esc destruyen el túnel y todos sus recursos.",
                    id="tunnel-note",
                    classes="subtitle",
                )
                with Horizontal(id="tunnel-buttons", classes="btn-group"):
                    yield Button(
                        "Destruir Túnel y Salir",
                        id="btn-tunnel-destroy",
                        variant="error",
                        classes="btn-danger",
                    )
        yield Footer()

    def on_mount(self) -> None:
        """Render the session details and start the uptime ticker."""
        self._started_at = time.time()
        self._refresh_details()
        self._ticker = self.set_interval(1, self._tick)

    def on_unmount(self) -> None:
        """Stop the ticker when leaving the screen."""
        ticker = getattr(self, "_ticker", None)
        if ticker is not None:
            ticker.stop()
            self._ticker = None

    def _tick(self) -> None:
        """Refresh the uptime and tunnel health once per second."""
        self._refresh_uptime()
        self._refresh_health()

    @property
    def _deployment(self):
        """Last successful deployment recorded in the app state."""
        return getattr(self.app.state, "last_deployment", None)

    def _refresh_details(self) -> None:
        """Fill the panel with the session's identity and endpoint."""
        state = self.app.state
        deployment = self._deployment

        if deployment is None:
            self.query_one("#tunnel-session", Static).update(
                "[yellow]Sin despliegue activo.[/yellow]"
            )
            self.query_one("#tunnel-endpoint", Static).update("")
            self.query_one("#tunnel-instance", Static).update("")
            return

        provider_display = get_provider_display_name(state.provider_name)
        self.query_one("#tunnel-session", Static).update(
            f"[dim]Proveedor:[/dim] {provider_display}"
            f"   [dim]Región:[/dim] {state.selected_region}"
        )
        self.query_one("#tunnel-endpoint", Static).update(
            f"[dim]IP Pública:[/dim] [bold yellow]{deployment['public_ip']}[/bold yellow]"
            f"   [dim]WireGuard:[/dim] UDP {deployment['wireguard_port']}"
        )
        self.query_one("#tunnel-instance", Static).update(
            f"[dim]Instancia:[/dim] {deployment['instance_id']}"
            f"   [dim]IP Privada:[/dim] {deployment['private_ip']}"
        )
        self._refresh_uptime()

    def _refresh_uptime(self) -> None:
        """Update the elapsed-time row."""
        session = read_active_session()
        if session is not None and session.started_at:
            elapsed = session.uptime_seconds
        else:
            elapsed = max(0.0, time.time() - self._started_at)
        hours, remainder = divmod(int(elapsed), 3600)
        minutes, seconds = divmod(remainder, 60)
        self.query_one("#tunnel-uptime", Static).update(
            f"[dim]Activo desde:[/dim] {hours:d}h {minutes:02d}m {seconds:02d}s"
        )

    def _refresh_health(self) -> None:
        """Poll the local daemon and report whether wg0 is still up."""
        try:
            from wisp.wireguard import status_wireguard_client

            response = status_wireguard_client()
        except Exception as exc:
            logger.debug(f"Tunnel health check failed: {exc}")
            self.query_one("#tunnel-health", Static).update(
                "[yellow]Estado local: desconocido (daemon inaccesible)[/yellow]"
            )
            return

        if response.ok:
            self.query_one("#tunnel-health", Static).update(
                f"[bold green]● Túnel establecido[/bold green]"
                f" [dim]{response.message or 'wg0 activo'}[/dim]"
            )
        else:
            self.query_one("#tunnel-health", Static).update(
                "[bold yellow]● Interfaz local caída[/bold yellow]"
                f" [dim]{response.message}[/dim]"
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-tunnel-destroy":
            self.action_destroy()

    def action_destroy(self) -> None:
        """Destroy the tunnel and its resources, then exit.

        The shutdown screen owns the teardown so the user sees progress: a
        cloud destroy blocks for minutes and would otherwise look like a hang.
        Unless confirmations were disabled in ``[general]``, a modal asks first
        — a destroyed tunnel is the one thing on this screen that is
        irreversible (there is deliberately no way back to the menu).
        """
        state = self.app.state  # type: ignore[attr-defined]
        if state.config.confirm_destroy:
            self.app.push_screen(ConfirmDestroyScreen(), self._handle_destroy_choice)
        else:
            request_shutdown(self.app, "tunnel destroyed from the tunnel screen")

    def _handle_destroy_choice(self, choice: tuple[bool, bool] | None) -> None:
        """Apply the destroy modal's verdict: proceed, and maybe stop asking."""
        if choice is None or not choice[0]:
            return

        # The switch asks to stop confirming; persist it so the preference
        # survives restarts (save_session_config only touches [general], keeping
        # every other section — and the secrets — intact).
        _, no_ask = choice
        if no_ask:
            state = self.app.state  # type: ignore[attr-defined]
            state.config.confirm_destroy = False
            try:
                save_session_config(state.config)
            except Exception as exc:
                logger.warning(f"Could not persist confirm_destroy: {exc}")

        request_shutdown(self.app, "tunnel destroyed from the tunnel screen")
