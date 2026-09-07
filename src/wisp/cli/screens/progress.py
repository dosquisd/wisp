"""Progress screen: full-bleed pipeline runner with live telemetry stream."""

import time
from datetime import datetime

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, ProgressBar, Static

from wisp.providers.aws import AWSProvider
from wisp.providers.base import DeployVMResult


class ProgressScreen(Screen):
    """Drives deployment or destruction in a background worker with a live log stream."""

    BINDINGS = [
        Binding("escape", "back", "Back", show=True),
        Binding("d", "destroy", "Destroy", show=False),
    ]

    def compose(self) -> ComposeResult:
        state = self.app.state  # type: ignore[attr-defined]
        cfg = state.config
        port_str = (
            f"UDP {cfg.wireguard_port}" if cfg.wireguard_port > 0 else "Dynamic random"
        )
        yield Header(show_clock=True)

        # Top breadcrumb bar
        with Horizontal(classes="app-top-bar"):
            with Horizontal(classes="breadcrumb"):
                yield Static(
                    "[bold cyan]wisp[/bold cyan] [dim]›[/dim] [white]deploy pipeline[/white]"
                )
            with Horizontal(classes="top-badges"):
                yield Static(
                    "[bold black on #f59e0b] DEPLOYING (STAGE 3/6) [/bold black on #f59e0b]",
                    id="pipeline-top-badge",
                )

        # Multi-pane split layout
        with Horizontal(classes="split-layout"):
            # Left Sidebar: Pipeline stages
            with Vertical(classes="sidebar"):
                yield Static("PIPELINE STAGES", classes="sidebar-section-title")
                with Vertical(id="stages-container"):
                    yield Static(self._build_stages_text(), id="stages-list")

                with Vertical(classes="context-box"):
                    yield Static("[bold white]DEPLOY SPEC[/bold white]")
                    yield Static(
                        f"[dim]• Cloud:[/dim] [cyan]{state.provider_name.upper()}[/cyan]"
                    )
                    yield Static(
                        f"[dim]• Region:[/dim] [yellow]{state.selected_region}[/yellow]"
                    )
                    yield Static("[dim]• Instance:[/dim] [white]t3.micro[/white]")
                    yield Static(f"[dim]• Port:[/dim] [white]{port_str}[/white]")
                    yield Static(
                        f"[dim]• Firewall:[/dim] [white]{'Caller /32' if cfg.force_current_ip else '0.0.0.0/0'}[/white]"
                    )

            # Right Main Workspace: Live telemetry & logs
            with Vertical(classes="main-workspace"):
                # Top Status Card
                with Vertical(classes="workspace-card", id="progress-top-card"):
                    with Horizontal(classes="card-header-row"):
                        yield Static(
                            "[bold white]STEP 3/6: PROVISIONING EC2 & FIREWALL RULES[/bold white]",
                            id="progress-step-title",
                        )
                        yield Static(
                            "[bold amber]ELAPSED: 00:00s[/bold amber]",
                            id="progress-elapsed",
                        )

                    yield ProgressBar(id="progress-bar", total=100, show_eta=False)
                    yield Static(
                        "[dim]Running: Pulumi automation engine (EC2 KeyPair, SG, Instance)...[/dim]",
                        id="progress-status-msg",
                    )

                # Results Box (shown on completion)
                with Vertical(classes="workspace-card", id="results-box"):
                    yield Static("", id="results-content")

                # Live Terminal Log Stream
                with Vertical(classes="workspace-card", id="log-card"):
                    with Horizontal(classes="card-header-row"):
                        yield Static("[bold white]LIVE CONSOLE STREAM[/bold white]")
                        yield Static("[green]AUTO-SCROLL: ON[/green]")

                    with ScrollableContainer(id="log-stream-box"):
                        yield Static(self._initial_log_stream(), id="log-content")

                # Action buttons
                with Horizontal(classes="btn-group", id="progress-buttons"):
                    yield Button(
                        "Return to Menu (Esc)",
                        id="btn-progress-back",
                        variant="primary",
                    )
                    yield Button(
                        "Destroy VPN", id="btn-progress-destroy", variant="error"
                    )

        yield Footer()

    def on_mount(self) -> None:
        self.start_time = time.time()
        self.logs_history = [self._initial_log_stream()]
        self.current_stage = 3
        self.query_one("#results-box").styles.display = "none"
        self.query_one("#progress-buttons").styles.display = "none"
        self.set_interval(1.0, self._update_elapsed_timer)
        self.start_deployment()

    def _initial_log_stream(self) -> str:
        now = datetime.now().strftime("%H:%M:%S")
        return f"[dim]{now}[/dim] [bold cyan][INFO ][/bold cyan] Initializing Pulumi Automation API workspace (stack: wisp-stack)..."

    def _update_elapsed_timer(self) -> None:
        try:
            elapsed = int(time.time() - self.start_time)
            mins = elapsed // 60
            secs = elapsed % 60
            self.query_one("#progress-elapsed", Static).update(
                f"[bold amber]ELAPSED: {mins:02d}:{secs:02d}s[/bold amber]"
            )
        except Exception:
            pass

    def _build_stages_text(self) -> str:
        stage = getattr(self, "current_stage", 3)
        s1 = "[bold green]✓ 01. Provider Selection[/bold green]\n   [dim]AWS configured[/dim]\n"
        s2 = "[bold green]✓ 02. Region Resolution[/bold green]\n   [dim]Target zone active[/dim]\n"

        if stage < 3:
            s3 = "[dim]○ 03. VM & Security Group[/dim]\n   [dim]Pulumi Automation API[/dim]\n"
        elif stage == 3:
            s3 = "[bold cyan]● 03. VM & Security Group[/bold cyan]\n   [cyan]Pulumi Automation API[/cyan]\n"
        else:
            s3 = "[bold green]✓ 03. VM & Security Group[/bold green]\n   [dim]Infrastructure created[/dim]\n"

        if stage < 4:
            s4 = "[dim]○ 04. OS Bootstrapping[/dim]\n   [dim]Wait SSH / cloud-init[/dim]\n"
        elif stage == 4:
            s4 = "[bold cyan]● 04. OS Bootstrapping[/bold cyan]\n   [cyan]Wait SSH / cloud-init[/cyan]\n"
        else:
            s4 = "[bold green]✓ 04. OS Bootstrapping[/bold green]\n   [dim]System online[/dim]\n"

        if stage < 5:
            s5 = "[dim]○ 05. Ansible WireGuard[/dim]\n   [dim]Install server & keys[/dim]\n"
        elif stage == 5:
            s5 = "[bold cyan]● 05. Ansible WireGuard[/bold cyan]\n   [cyan]Install server & keys[/cyan]\n"
        else:
            s5 = "[bold green]✓ 05. Ansible WireGuard[/bold green]\n   [dim]WireGuard ready[/dim]\n"

        if stage < 6:
            s6 = "[dim]○ 06. Tunnel Activation[/dim]\n   [dim]Connect via daemon[/dim]"
        elif stage == 6:
            s6 = "[bold cyan]● 06. Tunnel Activation[/bold cyan]\n   [cyan]Connect via daemon[/cyan]"
        else:
            s6 = "[bold green]✓ 06. Tunnel Activation[/bold green]\n   [dim]Tunnel connected[/dim]"

        return s1 + s2 + s3 + s4 + s5 + s6

    def start_deployment(self) -> None:
        self.run_deployment_worker()

    @work(thread=True)
    def run_deployment_worker(self) -> None:
        """Run deploy_vm off the UI thread, marshaling progress to UI."""
        state = self.app.state  # type: ignore[attr-defined]
        provider = AWSProvider()

        def on_progress(msg: str, progress: float | None) -> None:
            self.app.call_from_thread(self._handle_progress, msg, progress)

        try:
            result = provider.deploy_vm(
                region=state.selected_region,
                config=state.config,
                on_progress=on_progress,
            )
            self.app.call_from_thread(self._handle_success, result)
        except Exception as exc:
            self.app.call_from_thread(self._handle_error, str(exc))

    def _handle_progress(self, msg: str, progress: float | None) -> None:
        try:
            now = datetime.now().strftime("%H:%M:%S")
            self.query_one("#progress-status-msg", Static).update(f"[dim]{msg}[/dim]")

            if "Iniciando" in msg or "SSH" in msg or "Boot" in msg:
                self.current_stage = 4
            elif "Ansible" in msg or "WireGuard" in msg:
                self.current_stage = 5

            self.query_one("#stages-list", Static).update(self._build_stages_text())

            if progress is not None:
                pbar = self.query_one("#progress-bar", ProgressBar)
                pbar.progress = min(100, max(0, int(progress * 100)))

            # Append to live log stream
            log_line = f"[dim]{now}[/dim] [bold cyan][INFO ][/bold cyan] {msg}"
            self.logs_history.append(log_line)
            self.query_one("#log-content", Static).update(
                "\n".join(self.logs_history[-12:])
            )
        except Exception:
            pass

    def _handle_success(self, result: DeployVMResult) -> None:
        state = self.app.state  # type: ignore[attr-defined]
        state.last_deployment = result
        self.current_stage = 7

        try:
            self.query_one("#stages-list", Static).update(self._build_stages_text())
            self.query_one("#pipeline-top-badge", Static).update(
                "[bold white on #06281c] ● TUNNEL ACTIVE [/bold white on #06281c]"
            )
            self.query_one("#progress-bar", ProgressBar).progress = 100
            self.query_one("#progress-step-title", Static).update(
                "[bold green]✓ PIPELINE COMPLETED: VPN TUNNEL READY[/bold green]"
            )
            self.query_one("#progress-status-msg", Static).update(
                "[bold green]All 6 pipeline stages finished successfully.[/bold green]"
            )

            # Show results box
            res_content = (
                f"[bold green]● CONNECTION ESTABLISHED[/bold green]\n"
                f"[dim]• Instance ID:[/dim]  [white]{result['instance_id']}[/white]\n"
                f"[dim]• Public IP:[/dim]    [yellow]{result['public_ip']}[/yellow]\n"
                f"[dim]• WireGuard:[/dim]    [white]UDP {result['wireguard_port']}[/white]\n"
                f"[dim]• Private IP:[/dim]   [dim]{result['private_ip']}[/dim]"
            )
            self.query_one("#results-content", Static).update(res_content)
            self.query_one("#results-box").styles.display = "block"
            self.query_one("#progress-buttons").styles.display = "block"
            self.query_one("#btn-progress-back", Button).focus()
        except Exception:
            pass

    def _handle_error(self, error_msg: str) -> None:
        try:
            self.query_one("#pipeline-top-badge", Static).update(
                "[bold white on #260606] ✗ FAILED [/bold white on #260606]"
            )
            self.query_one("#progress-step-title", Static).update(
                "[bold red]✗ PIPELINE FAILED[/bold red]"
            )
            self.query_one("#progress-status-msg", Static).update(
                f"[red]Error: {error_msg}[/red]"
            )

            now = datetime.now().strftime("%H:%M:%S")
            self.logs_history.append(
                f"[dim]{now}[/dim] [bold red][ERROR][/bold red] {error_msg}"
            )
            self.query_one("#log-content", Static).update(
                "\n".join(self.logs_history[-12:])
            )

            self.query_one("#btn-progress-destroy", Button).styles.display = "none"
            self.query_one("#progress-buttons").styles.display = "block"
            self.query_one("#btn-progress-back", Button).focus()
        except Exception:
            pass

    @work(thread=True)
    def run_destruction_worker(self) -> None:
        state = self.app.state  # type: ignore[attr-defined]
        provider = AWSProvider()

        def on_progress(msg: str, progress: float | None) -> None:
            self.app.call_from_thread(self._handle_progress, msg, progress)

        try:
            provider.delete_vm(region=state.selected_region, on_progress=on_progress)
            self.app.call_from_thread(self._handle_destroy_success)
        except Exception as exc:
            self.app.call_from_thread(self._handle_error, str(exc))

    def _handle_destroy_success(self) -> None:
        state = self.app.state  # type: ignore[attr-defined]
        state.last_deployment = None

        try:
            self.query_one("#pipeline-top-badge", Static).update(
                "[bold black on #f59e0b] DESTROYED [/bold black on #f59e0b]"
            )
            self.query_one("#progress-step-title", Static).update(
                "[bold yellow]● INFRASTRUCTURE DESTROYED[/bold yellow]"
            )
            self.query_one("#results-box").styles.display = "none"
            self.query_one("#btn-progress-destroy", Button).styles.display = "none"
            self.query_one("#progress-buttons").styles.display = "block"
            self.query_one("#btn-progress-back", Button).focus()
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-progress-back":
            self.action_back()
        elif event.button.id == "btn-progress-destroy":
            self.start_destruction()

    def start_destruction(self) -> None:
        self.query_one("#pipeline-top-badge", Static).update(
            "[bold white on #260606] DESTROYING [/bold white on #260606]"
        )
        self.query_one("#progress-step-title", Static).update(
            "[bold red]● TEARING DOWN CLOUD RESOURCES[/bold red]"
        )
        self.query_one("#results-box").styles.display = "none"
        self.query_one("#progress-buttons").styles.display = "none"
        self.query_one("#progress-bar", ProgressBar).progress = 15
        self.run_destruction_worker()

    def action_back(self) -> None:
        self.app.pop_screen()
        if (
            len(self.app.screen_stack) > 1
            and type(self.app.screen).__name__ == "DeployScreen"
        ):
            self.app.pop_screen()
