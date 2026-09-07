"""Configuration screen: full-bleed split view with TOML persistence."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    OptionList,
    Static,
    Switch,
)
from textual.widgets.option_list import Option

from wisp.config.settings import WispConfig, get_config_file_path


class ConfigScreen(Screen):
    """Full-bleed form to edit deployment settings, persisting them to config.toml."""

    BINDINGS = [
        Binding("escape", "back", "Back", show=True),
        Binding("ctrl+s", "save", "Save", show=True),
        Binding("r", "reset", "Defaults", show=False),
    ]

    def compose(self) -> ComposeResult:
        cfg_path = get_config_file_path()
        yield Header(show_clock=True)

        # Top breadcrumb bar
        with Horizontal(classes="app-top-bar"):
            with Horizontal(classes="breadcrumb"):
                yield Static(
                    "[bold cyan]wisp[/bold cyan] [dim]›[/dim] [white]settings & toml[/white]"
                )
            with Horizontal(classes="top-badges"):
                yield Static(
                    "[bold cyan on #10192e] CONFIG.TOML (RW) [/bold cyan on #10192e]"
                )

        # Multi-pane split layout
        with Horizontal(classes="split-layout"):
            # Left Sidebar
            with Vertical(classes="sidebar"):
                yield Static("CATEGORIES", classes="sidebar-section-title")
                yield OptionList(
                    Option(
                        "› [1] Ansible & Boot    Timeouts & boot rules",
                        id="cat-ansible",
                    ),
                    Option("  [2] WireGuard Tunnel  Ports, iface & DNS", id="cat-wg"),
                    Option("  [3] Security/Firewall IP filtering rules", id="cat-sec"),
                    id="config-categories",
                )

                with Vertical(classes="context-box"):
                    yield Static("[bold white]FILE PERSISTENCE[/bold white]")
                    yield Static(f"[dim]• Target:[/dim] [cyan]{cfg_path.name}[/cyan]")
                    yield Static(
                        "[dim]• Status:[/dim] [green]Valid TOML format[/green]"
                    )
                    yield Static("[dim]• Shortcut:[/dim] [white]Ctrl+S to save[/white]")

            # Right Main Workspace
            with Vertical(classes="main-workspace"):
                with Vertical(classes="workspace-card"):
                    yield Static(
                        "[bold white]PARAMETERS CONFIGURATION (config.toml)[/bold white]"
                    )
                    yield Static(
                        "[dim]Values saved here are persisted and loaded automatically across all CLI and TUI sessions.[/dim]"
                    )

                with ScrollableContainer(classes="main-workspace", id="config-scroll"):
                    # Field: Ansible timeout
                    with Vertical(classes="field-card"):
                        yield Label(
                            "[bold white]Ansible Boot Timeout (seconds):[/bold white]"
                        )
                        yield Input(
                            id="input-ansible-timeout",
                            value=str(self.app.state.config.ansible_timeout),  # type: ignore[attr-defined]
                            type="integer",
                        )
                        yield Static(
                            "[dim]• Time allowed for EC2 cloud-init and sshd socket to become accessible[/dim]"
                        )

                    # Field: WireGuard port
                    with Vertical(classes="field-card"):
                        yield Label(
                            "[bold white]WireGuard UDP Port (0 for dynamic random 49152-65535):[/bold white]"
                        )
                        yield Input(
                            id="input-wireguard-port",
                            value=str(self.app.state.config.wireguard_port),  # type: ignore[attr-defined]
                            type="integer",
                        )
                        yield Static(
                            "[dim]• 0 assigns a cryptographic random high UDP port[/dim]"
                        )

                    # Field: Interface
                    with Vertical(classes="field-card"):
                        yield Label(
                            "[bold white]WireGuard Interface Name:[/bold white]"
                        )
                        yield Input(
                            id="input-wireguard-interface",
                            value=self.app.state.config.wireguard_interface,  # type: ignore[attr-defined]
                        )
                        yield Static(
                            "[dim]• Linux kernel wireguard network interface name (wg-quick)[/dim]"
                        )

                    # Field: Primary DNS
                    with Vertical(classes="field-card"):
                        yield Label("[bold white]Primary DNS Resolver:[/bold white]")
                        yield Input(
                            id="input-dns1",
                            value=self.app.state.config.wireguard_dns1,  # type: ignore[attr-defined]
                        )
                        yield Static(
                            "[dim]• Cloudflare privacy DNS resolver pushed to connected clients[/dim]"
                        )

                    # Field: Secondary DNS
                    with Vertical(classes="field-card"):
                        yield Label("[bold white]Secondary DNS Resolver:[/bold white]")
                        yield Input(
                            id="input-dns2",
                            value=self.app.state.config.wireguard_dns2,  # type: ignore[attr-defined]
                        )
                        yield Static("[dim]• Cloudflare fallback DNS resolver[/dim]")

                    # Field: Restrict IP
                    with Vertical(classes="field-card"):
                        with Horizontal(classes="field-top-row"):
                            yield Label(
                                "[bold white]Restrict Firewall Ingress to Caller Public IP (/32):[/bold white]"
                            )
                            yield Switch(
                                id="switch-force-ip",
                                value=self.app.state.config.force_current_ip,  # type: ignore[attr-defined]
                            )
                        yield Static(
                            "[dim]• When enabled, queries api.ipify.org and locks AWS SecurityGroup exclusively to your IP[/dim]"
                        )

                    yield Static("", id="error-message")

                    with Horizontal(classes="btn-group"):
                        yield Button(
                            "Save & Persist (Ctrl+S)", id="btn-save", variant="primary"
                        )
                        yield Button(
                            "Restore Defaults (R)", id="btn-reset", variant="default"
                        )
                        yield Button(
                            "Back to Menu (Esc)", id="btn-back", variant="default"
                        )

        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#input-ansible-timeout", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self.save_config()
        elif event.button.id == "btn-reset":
            self.reset_config()
        elif event.button.id == "btn-back":
            self.action_back()

    def action_save(self) -> None:
        self.save_config()

    def action_reset(self) -> None:
        self.reset_config()

    def save_config(self) -> None:
        """Validate form inputs, update state, and persist to config.toml."""
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
                error_label.update(
                    "[bold red][!] Boot timeout must be at least 5 seconds.[/bold red]"
                )
                return
        except ValueError:
            error_label.update(
                "[bold red][!] Boot timeout must be an integer.[/bold red]"
            )
            return

        try:
            port_val = int(port_raw)
            if port_val < 0 or port_val > 65535:
                error_label.update(
                    "[bold red][!] Port must be between 0 and 65535.[/bold red]"
                )
                return
        except ValueError:
            error_label.update("[bold red][!] Port must be an integer.[/bold red]")
            return

        if not interface:
            error_label.update(
                "[bold red][!] WireGuard interface cannot be empty.[/bold red]"
            )
            return

        if not dns1 or not dns2:
            error_label.update("[bold red][!] DNS servers cannot be empty.[/bold red]")
            return

        # Update in-memory state
        state = self.app.state  # type: ignore[attr-defined]
        state.config.ansible_timeout = timeout_val
        state.config.wireguard_port = port_val
        state.config.wireguard_interface = interface
        state.config.wireguard_dns1 = dns1
        state.config.wireguard_dns2 = dns2
        state.config.force_current_ip = force_ip

        # Persist to disk (config.toml)
        saved_path = state.config.save()

        self.notify(f"Saved configuration to {saved_path.name}", severity="information")
        self.app.pop_screen()

    def reset_config(self) -> None:
        """Reset the session config and repopulate the form with defaults."""
        state = self.app.state  # type: ignore[attr-defined]
        state.reset_config()

        default_cfg = WispConfig()
        self.query_one("#input-ansible-timeout", Input).value = str(
            default_cfg.ansible_timeout
        )
        self.query_one("#input-wireguard-port", Input).value = str(
            default_cfg.wireguard_port
        )
        self.query_one(
            "#input-wireguard-interface", Input
        ).value = default_cfg.wireguard_interface
        self.query_one("#input-dns1", Input).value = default_cfg.wireguard_dns1
        self.query_one("#input-dns2", Input).value = default_cfg.wireguard_dns2
        self.query_one("#switch-force-ip", Switch).value = default_cfg.force_current_ip

        self.query_one("#error-message", Static).update("")
        self.notify("Restored default configuration", severity="warning")

    def action_back(self) -> None:
        self.app.pop_screen()
