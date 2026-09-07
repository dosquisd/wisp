"""Main menu screen: zero-scroll compact dashboard with dual-pane layout."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, OptionList, Static
from textual.widgets.option_list import Option


class MainMenuScreen(Screen):
    """Full-bleed landing screen with zero-scroll compact layout."""

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

        # App top bar
        with Horizontal(classes="app-top-bar"):
            with Horizontal(classes="breadcrumb"):
                yield Static(
                    "[bold white]wisp[/bold white] [dim]›[/dim] [dim]overview[/dim]"
                )
            with Horizontal(classes="top-badges"):
                yield Static(self._get_daemon_badge())
                yield Static(self._get_cloud_badge(), id="cloud-badge")

        # Multi-pane split layout
        with Horizontal(classes="split-layout"):
            # Left Sidebar (compact 28 chars)
            with Vertical(classes="sidebar"):
                yield Static("NAVIGATION", classes="sidebar-section-title")
                yield OptionList(
                    Option("› [1] Deploy VPN", id="deploy"),
                    Option("  [2] Settings", id="config"),
                    Option("  [3] Telemetry", id="telemetry"),
                    Option("  [4] Teardown", id="destroy"),
                    Option("  [5] Quit", id="quit"),
                    id="menu-options",
                )

                with Vertical(classes="context-box"):
                    yield Static("[dim]SYSTEM CONTEXT[/dim]")
                    yield Static("[dim]• Daemon:[/dim] [green]/run/wisp.sock[/green]")
                    yield Static("[dim]• Tool:[/dim] [green]wg-quick[/green]")
                    yield Static("[dim]• Config:[/dim] [white]config.toml[/white]")
                    yield Static("[dim]• Privs:[/dim] [green]Unprivileged[/green]")

            # Right Main Workspace (Zero-Scroll Viewport)
            with Vertical(classes="main-workspace"):
                # Top Row: Split in 2 columns (Status & Specs)
                with Horizontal(classes="grid-2col"):
                    with Vertical(classes="workspace-card"):
                        yield Static(
                            "[dim]ACTIVE TUNNEL STATUS[/dim]",
                            classes="sidebar-section-title",
                        )
                        yield Static(
                            self._get_tunnel_status_text(), id="tunnel-status-text"
                        )

                    with Vertical(classes="workspace-card"):
                        yield Static(
                            "[dim]INFRASTRUCTURE SPEC[/dim]",
                            classes="sidebar-section-title",
                        )
                        yield Static(self._get_infra_spec_text(), id="infra-spec-text")

                # Middle Row: Compact 3-Column Configuration Matrix
                with Vertical(classes="workspace-card"):
                    yield Static(
                        "[dim]SESSION CONFIGURATION (config.toml)[/dim]",
                        classes="sidebar-section-title",
                    )
                    with Horizontal(classes="grid-3col"):
                        with Vertical(classes="grid-col3", id="cfg-col-1"):
                            yield Static(self._get_cfg_col1())
                        with Vertical(classes="grid-col3", id="cfg-col-2"):
                            yield Static(self._get_cfg_col2())
                        with Vertical(classes="grid-col3", id="cfg-col-3"):
                            yield Static(self._get_cfg_col3())

                # Bottom Row: Clean Callout Action Bar
                with Horizontal(classes="callout-action-box"):
                    yield Static(
                        "[bold white]› Press [1] or Enter to launch ephemeral cloud VPN[/bold white]",
                        classes="callout-text",
                    )
                    yield Static(
                        "[bold white on #27272a] ENTER ↵ [/bold white on #27272a]",
                        classes="callout-key",
                    )

        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#menu-options", OptionList).focus()

    def on_screen_resume(self) -> None:
        self.refresh_all_panels()
        self.query_one("#menu-options", OptionList).focus()

    def refresh_all_panels(self) -> None:
        """Refresh all live text widgets."""
        try:
            self.query_one("#cloud-badge", Static).update(self._get_cloud_badge())
            self.query_one("#tunnel-status-text", Static).update(
                self._get_tunnel_status_text()
            )
            self.query_one("#infra-spec-text", Static).update(
                self._get_infra_spec_text()
            )
            self.query_one("#cfg-col-1", Vertical).query_one(Static).update(
                self._get_cfg_col1()
            )
            self.query_one("#cfg-col-2", Vertical).query_one(Static).update(
                self._get_cfg_col2()
            )
            self.query_one("#cfg-col-3", Vertical).query_one(Static).update(
                self._get_cfg_col3()
            )
        except Exception:
            pass

    def _get_daemon_badge(self) -> str:
        return "[bold white on #18181b] ● DAEMON READY [/bold white on #18181b]"

    def _get_cloud_badge(self) -> str:
        state = self.app.state  # type: ignore[attr-defined]
        return f"[dim on #18181b] AWS: {state.selected_region} [/dim on #18181b]"

    def _get_tunnel_status_text(self) -> str:
        state = self.app.state  # type: ignore[attr-defined]
        if state.last_deployment:
            return (
                f"[dim]Status:[/dim]   [bold green]● ACTIVE[/bold green]\n"
                f"[dim]IP:[/dim]       [yellow]{state.last_deployment['public_ip']}[/yellow]\n"
                f"[dim]Machine:[/dim]  [white]{state.last_deployment['instance_id']}[/white]"
            )
        return (
            "[dim]Status:[/dim]   [bold green]● STANDBY (Ready)[/bold green]\n"
            "[dim]IP:[/dim]       [dim]None (disposable on demand)[/dim]\n"
            "[dim]Est Cost:[/dim] [white]$0.00 (pay-per-use)[/white]"
        )

    def _get_infra_spec_text(self) -> str:
        state = self.app.state  # type: ignore[attr-defined]
        return (
            f"[dim]Cloud:[/dim]    [white]AWS (Amazon EC2)[/white]\n"
            f"[dim]Region:[/dim]   [white]{state.selected_region}[/white]\n"
            f"[dim]VM Type:[/dim]  [white]t3.micro (Ubuntu 24.04)[/white]"
        )

    def _get_cfg_col1(self) -> str:
        cfg = self.app.state.config  # type: ignore[attr-defined]
        port_str = (
            f"UDP {cfg.wireguard_port}" if cfg.wireguard_port > 0 else "Dynamic UDP"
        )
        return f"[dim]Interface:[/dim] [white]{cfg.wireguard_interface}[/white]\n[dim]Port:[/dim]      [white]{port_str}[/white]"

    def _get_cfg_col2(self) -> str:
        cfg = self.app.state.config  # type: ignore[attr-defined]
        ip_mode = "Restricted (/32)" if cfg.force_current_ip else "Open (0.0.0.0/0)"
        return f"[dim]Timeout:[/dim]   [white]{cfg.ansible_timeout}s[/white]\n[dim]Firewall:[/dim]  [white]{ip_mode}[/white]"

    def _get_cfg_col3(self) -> str:
        cfg = self.app.state.config  # type: ignore[attr-defined]
        return f"[dim]DNS:[/dim]       [white]{cfg.wireguard_dns1}, {cfg.wireguard_dns2}[/white]\n[dim]Routing:[/dim]   [white]Full Tunnel[/white]"

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
