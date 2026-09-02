from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static


class MainMenuScreen(Screen):
    BINDINGS = [
        Binding("1", "deploy", "Desplegar", show=False),
        Binding("2", "config", "Configuración", show=False),
        Binding("3", "quit", "Salir", show=False),
    ]

    BANNER = (
        "[bold cyan]  █     █░ ██▓  ██████  ██▓███  \n"
        " ▓█░ █ ░█░▓██▒▒██    ▒ ▓██░  ██▒\n"
        " ▒█░ █ ░█ ▒██▒░ ▓██▄   ▓██░ ██▓▒\n"
        " ░█░ █ ░█ ░██░  ▒   ██▒▒██▄█▓▒ ▒\n"
        " ░░███▒███ ░██░▒██████▒▒▒██▒ ░  ░[/bold cyan]"
    )

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Center():
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
        try:
            status_widget = self.query_one("#status-preview", Static)
            status_widget.update(self._get_status_text())
        except Exception:
            pass

    def _get_status_text(self) -> str:
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
            f"[dim]Timeout:[/dim] [white]{cfg.ansible_timeout}s[/white]   "
            f"[dim]Puerto:[/dim] [white]{port_str}[/white]\n"
            f"[dim]Firewall:[/dim] [white]{ip_mode}[/white]\n"
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
