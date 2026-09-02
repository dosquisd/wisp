from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, ProgressBar, Static

from src.providers.aws import AWSProvider
from src.providers.base import DeployVMResult


class ProgressScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Volver", show=True),
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
        background: #0b0f19;
        border: round #10b981;
        padding: 1;
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
                    "[bold cyan]Despliegue en Curso[/bold cyan]",
                    id="progress-title",
                    classes="title",
                )
                yield Static(
                    "Aprovisionando recursos. Por favor no cierres la ventana.",
                    id="progress-subtitle",
                    classes="subtitle",
                )
                yield ProgressBar(id="progress-bar", total=100, show_eta=False)
                yield Static(
                    "Iniciando proceso de despliegue...",
                    id="progress-status-msg",
                )
                yield Static("", id="results-box")

                with Horizontal(id="progress-buttons", classes="btn-group"):
                    yield Button(
                        "Volver al Menú",
                        id="btn-progress-back",
                        variant="primary",
                        classes="btn-primary",
                    )
                    yield Button(
                        "Destruir VPN",
                        id="btn-progress-destroy",
                        variant="error",
                        classes="btn-danger",
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

        title.update("[bold cyan]Despliegue en Curso[/bold cyan]")
        state = self.app.state  # type: ignore[attr-defined]
        subtitle.update(
            f"Desplegando en AWS ([yellow]{state.selected_region}[/yellow])..."
        )
        pbar.styles.display = "block"
        pbar.progress = 5
        status_msg.styles.display = "block"
        status_msg.update("Iniciando infraestructura...")
        results.styles.display = "none"
        buttons.styles.display = "none"

    @work(thread=True)
    def run_deployment_worker(self) -> None:
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

        title.update("[bold green]✓ VPN Desplegada y Activa[/bold green]")
        subtitle.update("La máquina virtual y el túnel WireGuard están listos.")
        pbar.styles.display = "none"
        status_msg.styles.display = "none"

        results_text = (
            f"[bold green]Estado:[/bold green] Activa\n"
            f"[bold cyan]ID de Instancia:[/bold cyan] {result['instance_id']}\n"
            f"[bold cyan]IP Pública:[/bold cyan] [yellow]{result['public_ip']}[/yellow]\n"
            f"[bold cyan]Puerto WireGuard:[/bold cyan] UDP {result['wireguard_port']}\n"
            f"[bold cyan]IP Privada:[/bold cyan] {result['private_ip']}"
        )
        results.update(results_text)
        results.styles.border = ("round", "#10b981")
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

        title.update("[bold red]✗ Error en la Operación[/bold red]")
        subtitle.update("Ocurrió un problema durante el proceso:")
        pbar.styles.display = "none"

        status_msg.update(f"[red]{error_msg}[/red]")
        status_msg.styles.display = "block"

        destroy_btn.styles.display = "none"
        buttons.styles.display = "block"

    @work(thread=True)
    def run_destruction_worker(self) -> None:
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

        title.update("[bold yellow]✓ VPN Destruida[/bold yellow]")
        subtitle.update("Todos los recursos en la nube han sido eliminados.")
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

        title.update("[bold red]Destruyendo Recursos...[/bold red]")
        subtitle.update("Eliminando instancia EC2 y Security Group en AWS.")
        results.styles.display = "none"
        buttons.styles.display = "none"
        pbar.styles.display = "block"
        pbar.progress = 20
        status_msg.styles.display = "block"
        status_msg.update("Contactando a Pulumi...")

        self.run_destruction_worker()

    def action_back(self) -> None:
        # Return to main menu screen
        self.app.pop_screen()
        # If deploy screen was also pushed, pop it to return to main menu
        if len(self.app.screen_stack) > 1 and type(self.app.screen).__name__ == "DeployScreen":
            self.app.pop_screen()
