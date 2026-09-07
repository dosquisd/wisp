"""Progress screen: runs deploy/destroy in a worker thread and shows results."""

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, ProgressBar, Static

from wisp.providers.aws import AWSProvider
from wisp.providers.base import DeployVMResult


class ProgressScreen(Screen):
    """Drives a deploy (and optional destroy) and renders live progress."""

    BINDINGS = [
        Binding("escape", "back", "Back", show=True),
    ]

    CSS = """
    #progress-status-msg {
        text-align: center;
        color: #38bdf8;
        margin-top: 1;
        margin-bottom: 1;
        height: 2;
    }

    #results-box {
        display: none;
        background: #090d16;
        border: solid #10b981;
        padding: 1 2;
        margin-top: 1;
        margin-bottom: 1;
        height: auto;
    }

    #progress-buttons {
        display: none;
        height: 3;
        margin-top: 1;
    }

    .btn-group Button {
        margin-right: 1;
        width: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Center():
            with Vertical(classes="card"):
                yield Static(
                    "[bold cyan]● PROVISIONING INFRASTRUCTURE[/bold cyan]",
                    id="progress-title",
                    classes="cli-brand",
                )
                yield Static(
                    "Deploying resources. Please do not close this window.",
                    id="progress-subtitle",
                    classes="cli-tagline",
                )
                yield ProgressBar(id="progress-bar", total=100, show_eta=False)
                yield Static(
                    "Starting deployment pipeline...",
                    id="progress-status-msg",
                )
                yield Static("", id="results-box")

                with Horizontal(id="progress-buttons", classes="btn-group"):
                    yield Button(
                        "Return to Menu",
                        id="btn-progress-back",
                        variant="primary",
                    )
                    yield Button(
                        "Destroy VPN",
                        id="btn-progress-destroy",
                        variant="error",
                    )
        yield Footer()

    def on_mount(self) -> None:
        self.start_deployment()

    def start_deployment(self) -> None:
        self._set_deploying_ui()
        self.run_deployment_worker()

    def _set_deploying_ui(self) -> None:
        title = self.query_one("#progress-title", Static)
        subtitle = self.query_one("#progress-subtitle", Static)
        pbar = self.query_one("#progress-bar", ProgressBar)
        status_msg = self.query_one("#progress-status-msg", Static)
        results = self.query_one("#results-box", Static)
        buttons = self.query_one("#progress-buttons", Horizontal)

        title.update("[bold cyan]● PROVISIONING INFRASTRUCTURE[/bold cyan]")
        state = self.app.state  # type: ignore[attr-defined]
        subtitle.update(
            f"Deploying to AWS ([yellow]{state.selected_region}[/yellow])..."
        )
        pbar.styles.display = "block"
        pbar.progress = 5
        status_msg.styles.display = "block"
        status_msg.update("Starting Pulumi automation engine...")
        results.styles.display = "none"
        buttons.styles.display = "none"

    @work(thread=True)
    def run_deployment_worker(self) -> None:
        """Run ``deploy_vm`` off the UI thread, reporting progress and result."""
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
            status_msg = self.query_one("#progress-status-msg", Static)
            status_msg.update(msg)
            if progress is not None:
                pbar = self.query_one("#progress-bar", ProgressBar)
                pbar.progress = min(100, max(0, int(progress * 100)))
        except Exception:
            pass

    def _handle_success(self, result: DeployVMResult) -> None:
        state = self.app.state  # type: ignore[attr-defined]
        state.last_deployment = result

        title = self.query_one("#progress-title", Static)
        subtitle = self.query_one("#progress-subtitle", Static)
        pbar = self.query_one("#progress-bar", ProgressBar)
        status_msg = self.query_one("#progress-status-msg", Static)
        results = self.query_one("#results-box", Static)
        buttons = self.query_one("#progress-buttons", Horizontal)

        title.update("[bold green]● TUNNEL ACTIVE & READY[/bold green]")
        subtitle.update(
            "Virtual machine and WireGuard tunnel are connected and active."
        )
        pbar.styles.display = "none"
        status_msg.styles.display = "none"

        results_text = (
            f"[dim]STATUS[/dim]       [bold green]● ACTIVE[/bold green]\n"
            f"[dim]INSTANCE ID[/dim]  {result['instance_id']}\n"
            f"[dim]PUBLIC IP[/dim]    [yellow]{result['public_ip']}[/yellow]\n"
            f"[dim]WIREGUARD[/dim]    UDP {result['wireguard_port']}\n"
            f"[dim]PRIVATE IP[/dim]   {result['private_ip']}"
        )
        results.update(results_text)
        results.styles.border = ("solid", "#10b981")
        results.styles.display = "block"

        destroy_btn = self.query_one("#btn-progress-destroy", Button)
        destroy_btn.styles.display = "block"
        buttons.styles.display = "block"

    def _handle_error(self, error_msg: str) -> None:
        title = self.query_one("#progress-title", Static)
        subtitle = self.query_one("#progress-subtitle", Static)
        pbar = self.query_one("#progress-bar", ProgressBar)
        status_msg = self.query_one("#progress-status-msg", Static)
        buttons = self.query_one("#progress-buttons", Horizontal)
        destroy_btn = self.query_one("#btn-progress-destroy", Button)

        title.update("[bold red]✗ OPERATION FAILED[/bold red]")
        subtitle.update("An error occurred during execution:")
        pbar.styles.display = "none"

        status_msg.update(f"[red]{error_msg}[/red]")
        status_msg.styles.display = "block"

        destroy_btn.styles.display = "none"
        buttons.styles.display = "block"

    @work(thread=True)
    def run_destruction_worker(self) -> None:
        """Run ``delete_vm`` off the UI thread, reporting progress and result."""
        state = self.app.state  # type: ignore[attr-defined]
        provider = AWSProvider()

        def on_progress(msg: str, progress: float | None) -> None:
            self.app.call_from_thread(self._handle_progress, msg, progress)

        try:
            provider.delete_vm(
                region=state.selected_region,
                on_progress=on_progress,
            )
            self.app.call_from_thread(self._handle_destroy_success)
        except Exception as exc:
            self.app.call_from_thread(self._handle_error, str(exc))

    def _handle_destroy_success(self) -> None:
        state = self.app.state  # type: ignore[attr-defined]
        state.last_deployment = None

        title = self.query_one("#progress-title", Static)
        subtitle = self.query_one("#progress-subtitle", Static)
        pbar = self.query_one("#progress-bar", ProgressBar)
        status_msg = self.query_one("#progress-status-msg", Static)
        results = self.query_one("#results-box", Static)
        buttons = self.query_one("#progress-buttons", Horizontal)
        destroy_btn = self.query_one("#btn-progress-destroy", Button)

        title.update("[bold yellow]● INFRASTRUCTURE DESTROYED[/bold yellow]")
        subtitle.update("All cloud resources and keys have been removed.")
        pbar.styles.display = "none"
        results.styles.display = "none"
        status_msg.styles.display = "none"

        destroy_btn.styles.display = "none"
        buttons.styles.display = "block"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-progress-back":
            self.action_back()
        elif event.button.id == "btn-progress-destroy":
            self.start_destruction()

    def start_destruction(self) -> None:
        title = self.query_one("#progress-title", Static)
        subtitle = self.query_one("#progress-subtitle", Static)
        pbar = self.query_one("#progress-bar", ProgressBar)
        status_msg = self.query_one("#progress-status-msg", Static)
        results = self.query_one("#results-box", Static)
        buttons = self.query_one("#progress-buttons", Horizontal)

        title.update("[bold red]● TEARING DOWN INFRASTRUCTURE[/bold red]")
        subtitle.update("Disconnecting client and deleting AWS resources...")
        results.styles.display = "none"
        buttons.styles.display = "none"
        pbar.styles.display = "block"
        pbar.progress = 20
        status_msg.styles.display = "block"
        status_msg.update("Connecting to Pulumi engine...")

        self.run_destruction_worker()

    def action_back(self) -> None:
        """Return to the main menu screen."""
        self.app.pop_screen()
        if (
            len(self.app.screen_stack) > 1
            and type(self.app.screen).__name__ == "DeployScreen"
        ):
            self.app.pop_screen()
