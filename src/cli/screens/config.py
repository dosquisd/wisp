from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static, Switch

from src.config.settings import WispConfig


class ConfigScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Volver", show=True),
    ]

    CSS = """
    #form-container {
        height: 11;
        margin-bottom: 1;
    }

    #form-container Label {
        color: #94a3b8;
        margin-top: 1;
    }

    #switch-row {
        height: 3;
        align: left middle;
        margin-top: 1;
        margin-bottom: 1;
    }

    #switch-row Label {
        margin-top: 0;
        margin-right: 2;
    }

    .btn-group {
        height: 3;
        margin-top: 1;
    }

    .btn-group Button {
        margin-right: 1;
        width: 1fr;
    }

    #error-message {
        color: #ef4444;
        text-align: center;
        height: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Center():
            with Vertical(classes="card"):
                yield Static(
                    "[bold cyan]Configuración de Sesión[/bold cyan]", classes="title"
                )
                yield Static(
                    "Modifica los parámetros para los despliegues de esta sesión.",
                    classes="subtitle",
                )

                with ScrollableContainer(id="form-container"):
                    yield Label("Timeout de Ansible (segundos para boot):")
                    yield Input(
                        id="input-ansible-timeout",
                        value=str(self.app.state.config.ansible_timeout),  # type: ignore[attr-defined]
                        type="integer",
                    )

                    yield Label("Puerto WireGuard (0 = aleatorio 49152-65535):")
                    yield Input(
                        id="input-wireguard-port",
                        value=str(self.app.state.config.wireguard_port),  # type: ignore[attr-defined]
                        type="integer",
                    )

                    yield Label("Interfaz de WireGuard:")
                    yield Input(
                        id="input-wireguard-interface",
                        value=self.app.state.config.wireguard_interface,  # type: ignore[attr-defined]
                    )

                    yield Label("DNS Primario:")
                    yield Input(
                        id="input-dns1",
                        value=self.app.state.config.wireguard_dns1,  # type: ignore[attr-defined]
                    )

                    yield Label("DNS Secundario:")
                    yield Input(
                        id="input-dns2",
                        value=self.app.state.config.wireguard_dns2,  # type: ignore[attr-defined]
                    )

                    with Horizontal(id="switch-row"):
                        yield Label("Restringir acceso solo a mi IP pública:")
                        yield Switch(
                            id="switch-force-ip",
                            value=self.app.state.config.force_current_ip,  # type: ignore[attr-defined]
                        )

                yield Static("", id="error-message")

                with Horizontal(classes="btn-group"):
                    yield Button(
                        "Guardar",
                        id="btn-save",
                        variant="primary",
                        classes="btn-primary",
                    )
                    yield Button(
                        "Restablecer",
                        id="btn-reset",
                        variant="default",
                        classes="btn-secondary",
                    )
                    yield Button(
                        "Volver",
                        id="btn-back",
                        variant="default",
                        classes="btn-secondary",
                    )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self.save_config()
        elif event.button.id == "btn-reset":
            self.reset_config()
        elif event.button.id == "btn-back":
            self.action_back()

    def save_config(self) -> None:
        timeout_raw = self.query_one("#input-ansible-timeout", Input).value.strip()
        port_raw = self.query_one("#input-wireguard-port", Input).value.strip()
        interface = self.query_one("#input-wireguard-interface", Input).value.strip()
        dns1 = self.query_one("#input-dns1", Input).value.strip()
        dns2 = self.query_one("#input-dns2", Input).value.strip()
        force_ip = self.query_one("#switch-force-ip", Switch).value

        error_label = self.query_one("#error-message", Static)

        try:
            timeout_val = int(timeout_raw)
            if timeout_val < 5:
                error_label.update("[!] El timeout debe ser de al menos 5 segundos.")
                return
        except ValueError:
            error_label.update("[!] El timeout debe ser un número entero.")
            return

        try:
            port_val = int(port_raw)
            if port_val < 0 or port_val > 65535:
                error_label.update("[!] El puerto debe estar entre 0 y 65535.")
                return
        except ValueError:
            error_label.update("[!] El puerto debe ser un número entero.")
            return

        if not interface:
            error_label.update("[!] La interfaz WireGuard no puede estar vacía.")
            return

        if not dns1 or not dns2:
            error_label.update("[!] Los servidores DNS no pueden estar vacíos.")
            return

        # Update in-memory state
        state = self.app.state  # type: ignore[attr-defined]
        state.config.ansible_timeout = timeout_val
        state.config.wireguard_port = port_val
        state.config.wireguard_interface = interface
        state.config.wireguard_dns1 = dns1
        state.config.wireguard_dns2 = dns2
        state.config.force_current_ip = force_ip

        self.notify("Configuración guardada en memoria", severity="information")
        self.app.pop_screen()

    def reset_config(self) -> None:
        state = self.app.state  # type: ignore[attr-defined]
        state.reset_config()

        default_cfg = WispConfig()
        self.query_one("#input-ansible-timeout", Input).value = str(
            default_cfg.ansible_timeout
        )
        self.query_one("#input-wireguard-port", Input).value = str(
            default_cfg.wireguard_port
        )
        self.query_one("#input-wireguard-interface", Input).value = (
            default_cfg.wireguard_interface
        )
        self.query_one("#input-dns1", Input).value = default_cfg.wireguard_dns1
        self.query_one("#input-dns2", Input).value = default_cfg.wireguard_dns2
        self.query_one("#switch-force-ip", Switch).value = default_cfg.force_current_ip

        self.query_one("#error-message", Static).update("")
        self.notify("Valores restablecidos por defecto", severity="warning")

    def action_back(self) -> None:
        self.app.pop_screen()
