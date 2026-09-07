"""Main menu screen: entry point with keyboard-driven options and live status."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, OptionList, Static
from textual.widgets.option_list import Option


class MainMenuScreen(Screen):
    """Landing screen with CLI-style keyboard navigation and live state."""

    BINDINGS = [
        Binding("1", "deploy", "Deploy", show=False),
        Binding("2", "config", "Settings", show=False),
        Binding("3", "quit", "Quit", show=False),
        Binding("q", "quit", "Quit", show=True),
        Binding("enter", "select_current", "Select", show=True),
    ]

    HEADER_BANNER = (
        "[bold cyan]wisp[/bold cyan] [dim]v0.1.0[/dim]  "
        "[dim]•[/dim]  [slate_300]ephemeral wireguard vpns on your own cloud[/slate_300]"
    )

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Center():
            with Vertical(classes="card"):
                yield Static(self.HEADER_BANNER, classes="cli-brand")
                yield Static(
                    "Navigate with [bold white]↑/↓[/bold white], press [bold cyan]Enter[/bold cyan] to select, or press [bold white]1-3[/bold white] directly.",
                    classes="cli-tagline",
                )
                yield Static(
                    self._get_status_text(),
                    id="status-preview",
                    classes="status-panel",
                )
                yield OptionList(
                    Option(
                        "› [1] Deploy VPN       Provision cloud VM and bring tunnel up",
                        id="deploy",
                    ),
                    Option(
                        "› [2] Settings         Configure timeouts, DNS, ports & security",
                        id="config",
                    ),
                    Option(
                        "› [3] Quit             Exit application",
                        id="quit",
                    ),
                    id="menu-options",
                )
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#menu-options", OptionList).focus()

    def on_screen_resume(self) -> None:
        self.update_status()
        self.query_one("#menu-options", OptionList).focus()

    def update_status(self) -> None:
        """Refresh the configuration and state summary panel."""
        try:
            status_widget = self.query_one("#status-preview", Static)
            status_widget.update(self._get_status_text())
        except Exception:
            pass

    def _get_status_text(self) -> str:
        """Build the clean status panel text."""
        state = self.app.state  # type: ignore[attr-defined]
        cfg = state.config
        port_str = (
            f"UDP {cfg.wireguard_port}"
            if cfg.wireguard_port > 0
            else "Dynamic (49152-65535)"
        )
        ip_mode = (
            "Current public IP only (/32)"
            if cfg.force_current_ip
            else "Open (0.0.0.0/0)"
        )

        if state.last_deployment:
            vpn_status = (
                f"[bold green]● ACTIVE[/bold green] "
                f"(IP: [yellow]{state.last_deployment['public_ip']}[/yellow], "
                f"ID: [white]{state.last_deployment['instance_id']}[/white])"
            )
        else:
            vpn_status = "[green]● READY[/green] (no active instance)"

        return (
            f"[dim]PROVIDER[/dim]  [bold cyan]{state.provider_name.upper()}[/bold cyan] [dim]({state.selected_region})[/dim]   "
            f"[dim]TIMEOUT[/dim]  [white]{cfg.ansible_timeout}s[/white]   "
            f"[dim]PORT[/dim]  [white]{port_str}[/white]\n"
            f"[dim]FIREWALL[/dim]  [white]{ip_mode}[/white]   "
            f"[dim]STATUS[/dim]    {vpn_status}"
        )

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_id == "deploy":
            self.action_deploy()
        elif event.option_id == "config":
            self.action_config()
        elif event.option_id == "quit":
            self.action_quit()

    def action_select_current(self) -> None:
        opt_list = self.query_one("#menu-options", OptionList)
        idx = opt_list.highlighted
        if idx == 0:
            self.action_deploy()
        elif idx == 1:
            self.action_config()
        elif idx == 2:
            self.action_quit()

    def action_deploy(self) -> None:
        self.app.push_screen("deploy")

    def action_config(self) -> None:
        self.app.push_screen("config")

    def action_quit(self) -> None:
        self.app.exit()
