"""Configuration screen: compact two-column form with theme selector and TOML persistence."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    OptionList,
    Select,
    Static,
    Switch,
)
from textual.widgets.option_list import Option

from wisp.config.settings import WispConfig, get_config_file_path


class ConfigScreen(Screen):
    """Compact form to edit deployment parameters, theme, and persistence."""

    BINDINGS = [
        Binding("escape", "back", "Back", show=True),
        Binding("ctrl+s", "save", "Save", show=True),
        Binding("r", "reset", "Defaults", show=False),
    ]

    def compose(self) -> ComposeResult:
        cfg_path = get_config_file_path()
        cfg = self.app.state.config  # type: ignore[attr-defined]
        yield Header(show_clock=True)

        # Top breadcrumb bar
        with Horizontal(classes="app-top-bar"):
            with Horizontal(classes="breadcrumb"):
                yield Static(
                    "[bold white]wisp[/bold white] [dim]›[/dim] [dim]settings & toml[/dim]"
                )
            with Horizontal(classes="top-badges"):
                yield Static("[dim on #18181b] CONFIG.TOML (RW) [/dim on #18181b]")

        # Multi-pane split layout
        with Horizontal(classes="split-layout"):
            # Left Sidebar (compact 28 chars)
            with Vertical(classes="sidebar"):
                yield Static("CATEGORIES", classes="sidebar-section-title")
                yield OptionList(
                    Option("› [1] Core Engine", id="cat-1"),
                    Option("  [2] WireGuard", id="cat-2"),
                    Option("  [3] Visual Theme", id="cat-3"),
                    id="config-categories",
                )

                with Vertical(classes="context-box"):
                    yield Static("[dim]FILE PERSISTENCE[/dim]")
                    yield Static(f"[dim]• Path:[/dim] [white]{cfg_path.name}[/white]")
                    yield Static("[dim]• Format:[/dim] [green]Valid TOML[/green]")
                    yield Static("[dim]• Action:[/dim] [white]Ctrl+S saves[/white]")

            # Right Main Workspace (Zero-Scroll Viewport)
            with Vertical(classes="main-workspace"):
                with Vertical(classes="workspace-card"):
                    yield Static(
                        "[dim]CONFIGURATION PARAMETERS (config.toml)[/dim]",
                        classes="sidebar-section-title",
                    )

                    # Row 1: Timeout & Port
                    with Horizontal(classes="grid-2col"):
                        with Vertical(classes="grid-col"):
                            yield Label("[dim]Ansible Timeout (seconds):[/dim]")
                            yield Input(
                                id="input-ansible-timeout",
                                value=str(cfg.ansible_timeout),
                                type="integer",
                            )

                        with Vertical(classes="grid-col"):
                            yield Label("[dim]WireGuard Port (0 = dynamic):[/dim]")
                            yield Input(
                                id="input-wireguard-port",
                                value=str(cfg.wireguard_port),
                                type="integer",
                            )

                    # Row 2: Interface & Theme Palette
                    with Horizontal(classes="grid-2col"):
                        with Vertical(classes="grid-col"):
                            yield Label("[dim]Interface Name:[/dim]")
                            yield Input(
                                id="input-wireguard-interface",
                                value=cfg.wireguard_interface,
                            )

                        with Vertical(classes="grid-col"):
                            yield Label("[dim]Visual Theme Palette:[/dim]")
                            yield Select(
                                options=[
                                    ("Monochromatic Zinc (Default)", "zinc"),
                                    ("Warm Amber Phosphor", "amber"),
                                ],
                                value=getattr(cfg, "theme", "zinc"),
                                allow_blank=False,
                                id="select-theme",
                            )

                    # Row 3: Primary & Secondary DNS
                    with Horizontal(classes="grid-2col"):
                        with Vertical(classes="grid-col"):
                            yield Label("[dim]Primary DNS Resolver:[/dim]")
                            yield Input(
                                id="input-dns1",
                                value=cfg.wireguard_dns1,
                            )

                        with Vertical(classes="grid-col"):
                            yield Label("[dim]Secondary DNS Resolver:[/dim]")
                            yield Input(
                                id="input-dns2",
                                value=cfg.wireguard_dns2,
                            )

                    # Row 4: Restrict IP Switch
                    with Horizontal(classes="field-top-row"):
                        yield Label(
                            "[dim]Restrict Firewall to Caller Public IP (/32):[/dim]"
                        )
                        yield Switch(
                            id="switch-force-ip",
                            value=cfg.force_current_ip,
                        )

                yield Static("", id="error-message")

                # Bottom Action Buttons
                with Horizontal(classes="btn-group"):
                    yield Button(
                        "Save & Persist (Ctrl+S)", id="btn-save", variant="primary"
                    )
                    yield Button(
                        "Restore Defaults (R)", id="btn-reset", variant="default"
                    )
                    yield Button("Back to Menu (Esc)", id="btn-back", variant="default")

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
        theme_val = str(self.query_one("#select-theme", Select).value)

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
        state.config.theme = theme_val

        # Persist to disk (config.toml)
        saved_path = state.config.save()

        # Dynamically apply theme to application
        if hasattr(self.app, "apply_theme"):
            self.app.apply_theme()

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
        self.query_one("#select-theme", Select).value = default_cfg.theme

        self.query_one("#error-message", Static).update("")
        self.notify("Restored default configuration", severity="warning")

    def action_back(self) -> None:
        self.app.pop_screen()
