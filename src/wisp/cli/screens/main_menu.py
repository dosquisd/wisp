"""Main menu screen: full-bleed dashboard with multi-pane sidebar and workspace."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, OptionList, Static
from textual.widgets.option_list import Option


class MainMenuScreen(Screen):
    """Full-bleed landing screen with sidebar navigation and cloud telemetry."""

    BINDINGS = [
        Binding("1", "deploy", "Deploy", show=False),
        Binding("2", "config", "Settings", show=False),
        Binding("3", "telemetry", "Telemetry", show=False),
        Binding("4", "destroy", "Destroy", show=False),
        Binding("5", "quit", "Quit", show=False),
        Binding("q", "quit", "Quit", show=True),
        Binding("enter", "select_current", "Select", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        # App top bar with breadcrumbs and live badges
        with Horizontal(classes="app-top-bar"):
            with Horizontal(classes="breadcrumb"):
                yield Static(
                    "[bold cyan]wisp[/bold cyan] [dim]›[/dim] [white]overview[/white]"
                )
            with Horizontal(classes="top-badges", id="top-badges-container"):
                yield Static(self._get_daemon_badge())
                yield Static(self._get_cloud_badge(), id="cloud-badge")

        # Multi-pane full-bleed split layout
        with Horizontal(classes="split-layout"):
            # Left Sidebar
            with Vertical(classes="sidebar"):
                yield Static("NAVIGATION", classes="sidebar-section-title")
                yield OptionList(
                    Option(
                        "› [1] Deploy VPN       Launch cloud VM tunnel", id="deploy"
                    ),
                    Option("  [2] Settings         Edit config.toml", id="config"),
                    Option(
                        "  [3] Telemetry        View connection info", id="telemetry"
                    ),
                    Option("  [4] Teardown         Destroy active stack", id="destroy"),
                    Option("  [5] Quit             Exit session", id="quit"),
                    id="menu-options",
                )

                with Vertical(classes="context-box"):
                    yield Static("[bold white]SYSTEM HEALTH[/bold white]")
                    yield Static(
                        "[dim]• Daemon Socket:[/dim] [green]/run/wisp.sock[/green]"
                    )
                    yield Static("[dim]• WireGuard Tool:[/dim] [green]wg-quick[/green]")
                    yield Static(
                        "[dim]• Config Target:[/dim] [cyan]config.toml (user)[/cyan]"
                    )
                    yield Static(
                        "[dim]• Privileges:[/dim] [green]Unprivileged (safe)[/green]"
                    )

            # Right Main Workspace
            with Vertical(classes="main-workspace"):
                # Active Tunnel Card
                with Vertical(classes="workspace-card"):
                    with Horizontal(classes="card-header-row"):
                        yield Static(
                            "[bold white]ACTIVE TUNNEL & CLOUD OVERVIEW[/bold white]"
                        )
                        yield Static(
                            self._get_tunnel_status_badge(), id="tunnel-status-badge"
                        )

                    with Horizontal(classes="metric-row"):
                        with Vertical(classes="metric-chip"):
                            yield Static("[dim]TARGET CLOUD[/dim]")
                            yield Static("[bold cyan]AWS (EC2)[/bold cyan]")
                            yield Static("[dim]Ubuntu Noble 24.04[/dim]")

                        with Vertical(classes="metric-chip"):
                            yield Static("[dim]REGION[/dim]")
                            yield Static(self._get_region_chip(), id="metric-region")
                            yield Static("[dim]Low latency pool[/dim]")

                        with Vertical(classes="metric-chip"):
                            yield Static("[dim]INSTANCE[/dim]")
                            yield Static("[bold cyan]t3.micro[/bold cyan]")
                            yield Static("[dim]~$0.0104 / hr[/dim]")

                        with Vertical(classes="metric-chip"):
                            yield Static("[dim]ENCRYPTION[/dim]")
                            yield Static("[bold cyan]ChaCha20-Poly1305[/bold cyan]")
                            yield Static("[dim]Noise_IKpsk2[/dim]")

                # Active Settings Card
                with Vertical(classes="workspace-card"):
                    yield Static(
                        "[bold white]ACTIVE SESSION SETTINGS (config.toml)[/bold white]",
                        classes="card-header-row",
                    )
                    with Horizontal(classes="grid-2col"):
                        with Vertical(classes="grid-col", id="cfg-col-1"):
                            yield Static(self._get_cfg_col1())
                        with Vertical(classes="grid-col", id="cfg-col-2"):
                            yield Static(self._get_cfg_col2())

                # Quick Callout Action Box
                with Horizontal(classes="callout-action-box"):
                    yield Static(
                        "[bold cyan]›[/bold cyan] [bold white]Press [1] or Enter to launch an ephemeral cloud VPN now[/bold white]",
                        classes="callout-text",
                    )
                    yield Static(
                        "[bold black on cyan] ENTER ↵ [/bold black on cyan]",
                        classes="callout-key",
                    )

        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#menu-options", OptionList).focus()

    def on_screen_resume(self) -> None:
        self.refresh_all_panels()
        self.query_one("#menu-options", OptionList).focus()

    def refresh_all_panels(self) -> None:
        """Update all live dynamic badges and chips."""
        try:
            self.query_one("#cloud-badge", Static).update(self._get_cloud_badge())
            self.query_one("#tunnel-status-badge", Static).update(
                self._get_tunnel_status_badge()
            )
            self.query_one("#metric-region", Static).update(self._get_region_chip())
            self.query_one("#cfg-col-1", Vertical).query_one(Static).update(
                self._get_cfg_col1()
            )
            self.query_one("#cfg-col-2", Vertical).query_one(Static).update(
                self._get_cfg_col2()
            )
        except Exception:
            pass

    def _get_daemon_badge(self) -> str:
        return "[bold white on #06281c] ● DAEMON: ACTIVE [/bold white on #06281c]"

    def _get_cloud_badge(self) -> str:
        state = self.app.state  # type: ignore[attr-defined]
        return f"[bold cyan on #10192e] AWS: {state.selected_region} [/bold cyan on #10192e]"

    def _get_tunnel_status_badge(self) -> str:
        state = self.app.state  # type: ignore[attr-defined]
        if state.last_deployment:
            return f"[bold white on #06281c] ● ACTIVE (IP: {state.last_deployment['public_ip']}) [/bold white on #06281c]"
        return "[bold green on #182216] ● READY • STANDBY [/bold green on #182216]"

    def _get_region_chip(self) -> str:
        state = self.app.state  # type: ignore[attr-defined]
        return f"[bold cyan]{state.selected_region}[/bold cyan]"

    def _get_cfg_col1(self) -> str:
        cfg = self.app.state.config  # type: ignore[attr-defined]
        port_str = (
            f"UDP {cfg.wireguard_port}"
            if cfg.wireguard_port > 0
            else "Dynamic random (49152-65535)"
        )
        ip_mode = "Restricted (/32)" if cfg.force_current_ip else "Open (0.0.0.0/0)"
        return (
            f"[dim]Interface:[/dim]       [white]{cfg.wireguard_interface}[/white]\n"
            f"[dim]WireGuard Port:[/dim]  [white]{port_str}[/white]\n"
            f"[dim]Firewall Rule:[/dim]   [white]{ip_mode}[/white]"
        )

    def _get_cfg_col2(self) -> str:
        cfg = self.app.state.config  # type: ignore[attr-defined]
        return (
            f"[dim]Ansible Timeout:[/dim] [white]{cfg.ansible_timeout} seconds[/white]\n"
            f"[dim]DNS Resolvers:[/dim]   [white]{cfg.wireguard_dns1}, {cfg.wireguard_dns2}[/white]\n"
            f"[dim]Tunnel Routing:[/dim]  [white]Full Tunnel (all traffic via VPN)[/white]"
        )

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_id == "deploy":
            self.action_deploy()
        elif event.option_id == "config":
            self.action_config()
        elif event.option_id == "telemetry":
            self.action_telemetry()
        elif event.option_id == "destroy":
            self.action_destroy()
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
            self.action_telemetry()
        elif idx == 3:
            self.action_destroy()
        elif idx == 4:
            self.action_quit()

    def action_deploy(self) -> None:
        self.app.push_screen("deploy")

    def action_config(self) -> None:
        self.app.push_screen("config")

    def action_telemetry(self) -> None:
        state = self.app.state  # type: ignore[attr-defined]
        if state.last_deployment:
            self.notify(
                f"Active VPN: {state.last_deployment['public_ip']} (Port {state.last_deployment['wireguard_port']})",
                title="Tunnel Telemetry",
                severity="information",
            )
        else:
            self.notify(
                "No active VPN tunnel deployed.",
                title="Tunnel Telemetry",
                severity="warning",
            )

    def action_destroy(self) -> None:
        state = self.app.state  # type: ignore[attr-defined]
        if not state.last_deployment:
            self.notify(
                "No active VPN deployment found to destroy.", severity="warning"
            )
            return
        self.app.push_screen("deploy")

    def action_quit(self) -> None:
        self.app.exit()
