"""Progress screen: zero-scroll pipeline runner with live telemetry stream."""

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
    """Zero-scroll pipeline runner with live console log stream."""

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
                    "[bold white]wisp[/bold white] [dim]›[/dim] [dim]deploy pipeline[/dim]"
                )
            with Horizontal(classes="top-badges"):
                yield Static(
                    "[bold black on #f59e0b] DEPLOYING (STAGE 3/6) [/bold black on #f59e0b]",
                    id="pipeline-top-badge",
                )

        # Multi-pane split layout
        with Horizontal(classes="split-layout"):
            # Left Sidebar (compact 28 chars)
            with Vertical(classes="sidebar"):
                yield Static("PIPELINE STAGES", classes="sidebar-section-title")
                with Vertical(id="stages-container"):
                    yield Static(self._build_stages_text(), id="stages-list")

                with Vertical(classes="context-box"):
                    yield Static("[dim]DEPLOY SPEC[/dim]")
                    yield Static(
                        f"[dim]• Cloud:[/dim] [white]{state.provider_name.upper()}[/white]"
                    )
                    yield Static(
                        f"[dim]• Region:[/dim] [yellow]{state.selected_region}[/yellow]"
                    )
                    yield Static("[dim]• Instance:[/dim] [white]t3.micro[/white]")
                    yield Static(f"[dim]• Port:[/dim] [white]{port_str}[/white]")
                    yield Static(
                        f"[dim]• Access:[/dim] [white]{'Caller /32' if cfg.force_current_ip else 'Open 0.0.0.0/0'}[/white]"
                    )

            # Right Main Workspace (Zero-Scroll Viewport)
            with Vertical(classes="main-workspace"):
                # Top Status Card
                with Vertical(classes="workspace-card", id="progress-top-card"):
                    with Horizontal(classes="card-header-row"):
                        yield Static(
                            "[dim]STAGE 3/6: PROVISIONING EC2 & SECURITY GROUP[/dim]",
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

                # Results Box (hidden until completed)
                with Vertical(classes="workspace-card", id="results-box"):
                    yield Static("", id="results-content")

                # Live Terminal Log Stream Box
                with Vertical(classes="workspace-card", id="log-card"):
                    with Horizontal(classes="card-header-row"):
                        yield Static("[dim]LIVE CONSOLE STREAM[/dim]")
                        yield Static("[green]AUTO-SCROLL: ON[/green]")

                    with ScrollableContainer(id="log-stream-box"):
                        yield Static(self._initial_log_stream(), id="log-content")

                # Action Buttons
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
        return f"[dim]{now}[/dim] [INFO ] Initializing Pulumi Automation API workspace (stack: wisp-stack)..."

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
        s1 = "[green]✓[/green] 01. Cloud Provider\n"
        s2 = "[green]✓[/green] 02. Region Target\n"

        if stage < 3:
            s3 = "[dim]○[/dim] 03. VM & Firewall\n"
        elif stage == 3:
            s3 = "[bold white]● 03. VM & Firewall[/bold white]\n"
        else:
            s3 = "[green]✓[/green] 03. VM & Firewall\n"

        if stage < 4:
            s4 = "[dim]○[/dim] 04. Bootstrapping\n"
        elif stage == 4:
            s4 = "[bold white]● 04. Bootstrapping[/bold white]\n"
        else:
            s4 = "[green]✓[/green] 04. Bootstrapping\n"

        if stage < 5:
            s5 = "[dim]○[/dim] 05. Ansible Setup\n"
        elif stage == 5:
            s5 = "[bold white]● 05. Ansible Setup[/bold white]\n"
        else:
            s5 = "[green]✓[/green] 05. Ansible Setup\n"

        if stage < 6:
            s6 = "[dim]○[/dim] 06. Tunnel Activate"
        elif stage == 6:
            s6 = "[bold white]● 06. Tunnel Activate[/bold white]"
        else:
            s6 = "[green]✓[/green] 06. Tunnel Activate"

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

            log_line = f"[dim]{now}[/dim] [INFO ] {msg}"
            self.logs_history.append(log_line)
            self.query_one("#log-content", Static).update(
                "\n".join(self.logs_history[-8:])
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
                "[bold white on #18181b] ● TUNNEL ACTIVE [/bold white on #18181b]"
            )
            self.query_one("#progress-bar", ProgressBar).progress = 100
            self.query_one("#progress-step-title", Static).update(
                "[bold green]✓ PIPELINE COMPLETED: VPN READY[/bold green]"
            )
            self.query_one("#progress-status-msg", Static).update(
                "[bold green]All 6 pipeline stages finished successfully.[/bold green]"
            )

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
                "[bold white on #7f1d1d] ✗ FAILED [/bold white on #7f1d1d]"
            )
            self.query_one("#progress-step-title", Static).update(
                "[bold red]✗ PIPELINE FAILED[/bold red]"
            )
            self.query_one("#progress-status-msg", Static).update(
                f"[red]Error: {error_msg}[/red]"
            )

            now = datetime.now().strftime("%H:%M:%S")
            self.logs_history.append(f"[dim]{now}[/dim] [ERROR] {error_msg}")
            self.query_one("#log-content", Static).update(
                "\n".join(self.logs_history[-8:])
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
            "[bold white on #7f1d1d] DESTROYING [/bold white on #7f1d1d]"
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
