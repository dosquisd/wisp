"""Main menu screen: entry point with a live configuration summary."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import CenterMiddle, Vertical
from textual.widgets import Button, Footer, Header, Static

from wisp.cli.screens.base import WispScreen


class MainMenuScreen(WispScreen):
    """Landing screen; shows current config and navigates to other screens."""

    BINDINGS = [
        Binding("1", "deploy", "Desplegar", show=True),
        Binding("2", "config", "Configuración", show=True),
        Binding("3", "quit", "Salir", show=True),
    ]

    # Rendered with the official figlet "ANSI Shadow" W/I/S/P glyphs
    # (no shade characters, every line padded to the same 29-column width
    # so the letters align exactly on any terminal).
    BANNER = (
        "[bold cyan]██╗    ██╗██╗███████╗██████╗ \n"
        "██║    ██║██║██╔════╝██╔══██╗\n"
        "██║ █╗ ██║██║███████╗██████╔╝\n"
        "██║███╗██║██║╚════██║██╔═══╝ \n"
        "╚███╔███╔╝██║███████║██║     \n"
        " ╚══╝╚══╝ ╚═╝╚══════╝╚═╝     [/bold cyan]"
    )

    # Scoped to this screen only (doesn't touch .title/.subtitle/.btn-* on
    # other screens, which legitimately need the roomier default spacing).
    # This menu is the one screen where scrolling to reach "Salir" is
    # actually bad UX — it's the exit door — so every row here is trimmed
    # to make the whole card fit without scrolling on a normal terminal.
    # Padding drops to 0 vertical (the round border already provides
    # visual separation) to offset the banner's sixth line.
    CSS = """
    MainMenuScreen .card {
        padding: 0 2;
    }

    MainMenuScreen .title {
        margin-bottom: 0;
    }

    MainMenuScreen .subtitle {
        margin-bottom: 0;
    }

    #status-preview {
        margin-bottom: 0;
    }

    #btn-deploy {
        margin-top: 1;
    }

    #btn-config, #btn-quit {
        margin-top: 0;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with CenterMiddle():
            with Vertical(classes="card"):
                yield Static(self.BANNER, classes="title")
                yield Static(
                    "VPNs efímeras de WireGuard bajo demanda", classes="subtitle"
                )
                yield Static(self._get_status_text(), id="status-preview")
                yield Button(
                    "1. Desplegar VPN",
                    id="btn-deploy",
                    variant="primary",
                    classes="btn-primary",
                )
                yield Button(
                    "2. Configuración",
                    id="btn-config",
                    variant="default",
                    classes="btn-secondary",
                )
                yield Button(
                    "3. Salir",
                    id="btn-quit",
                    variant="error",
                    classes="btn-danger",
                )
        yield Footer()

    def on_screen_resume(self) -> None:
        self.update_status()

    def update_status(self) -> None:
        """Refresh the configuration summary widget."""
        try:
            status_widget = self.query_one("#status-preview", Static)
            status_widget.update(self._get_status_text())
        except Exception:
            pass

    def _get_status_text(self) -> str:
        """Build the provider/region/config summary shown on the menu."""
        state = self.app.state  # type: ignore[attr-defined]
        cfg = state.config
        port_str = (
            f"UDP {cfg.wireguard_port}"
            if cfg.wireguard_port > 0
            else "Aleatorio (49152-65535)"
        )
        ip_mode = (
            "Solo mi IP actual (/32)"
            if cfg.force_current_ip
            else "Cualquier IP (0.0.0.0/0)"
        )
        return (
            f"[dim]Proveedor:[/dim] [cyan]{state.provider_name.upper()}[/cyan]   "
            f"[dim]Región:[/dim] [yellow]{state.selected_region}[/yellow]\n"
            f"[dim]Timeout:[/dim] [white]{cfg.vm_boot_timeout}s[/white]   "
            f"[dim]Puerto:[/dim] [white]{port_str}[/white]\n"
            f"[dim]Firewall:[/dim] [white]{ip_mode}[/white]"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-deploy":
            self.action_deploy()
        elif event.button.id == "btn-config":
            self.action_config()
        elif event.button.id == "btn-quit":
            self.app.exit()

    def action_deploy(self) -> None:
        self.app.push_screen("deploy")

    def action_config(self) -> None:
        self.app.push_screen("config")

    def action_quit(self) -> None:
        self.app.exit()
