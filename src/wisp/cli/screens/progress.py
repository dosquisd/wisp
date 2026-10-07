"""Progress screen: runs deploy/destroy in a worker thread and shows results."""

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, ProgressBar, Static

from wisp.cli.screens.base import WispScreen
from wisp.cli.screens.modal import ConfirmDestroyScreen
from wisp.cli.screens.shutdown import request_shutdown
from wisp.cli.screens.tunnel import TunnelScreen
from wisp.config.settings import save_session_config
from wisp.providers import PROVIDERS_MAP, ProviderEnum
from wisp.providers.base import DeployVMResult, get_provider_display_name
from wisp.session import teardown_active_session, write_active_session
from wisp.utils import logger


class ProgressScreen(WispScreen):
    """Drives a deploy (and optional destroy) and renders live progress.

    Provider calls run in Textual worker threads; UI updates are marshaled back
    to the UI thread via ``self.app.call_from_thread``.
    """

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

    /* A ProgressBar hugs its natural width against the left edge; wrapping it
       in a full-width Center puts it in the middle of the card. Textual has no
       `margin: auto`/percentage margins, so the container is the only lever. */
    #progress-bar-center {
        width: 100%;
    }

    #progress-bar {
        width: 50;
    }
    """

    def __init__(self) -> None:
        """Initialize the screen with no deployment in flight."""
        super().__init__()
        self._deploying = False

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
                with Center(id="progress-bar-center"):
                    yield ProgressBar(
                        id="progress-bar",
                        total=100,
                        show_eta=False,
                        show_percentage=True,
                    )
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

    def _get_provider(self):
        """Get the provider instance based on state."""
        state = self.app.state  # type: ignore[attr-defined]
        provider_cls = PROVIDERS_MAP[ProviderEnum(state.provider_name)]
        return provider_cls()

    def _get_provider_name(self) -> str:
        """Get the provider display name."""
        state = self.app.state  # type: ignore[attr-defined]
        return get_provider_display_name(state.provider_name)

    def start_deployment(self) -> None:
        self._deploying = True
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
        provider_name = self._get_provider_name()
        subtitle.update(
            f"Desplegando en {provider_name} ([yellow]{state.selected_region}[/yellow])..."
        )
        pbar.styles.display = "block"
        pbar.progress = 5
        status_msg.styles.display = "block"
        status_msg.update("Iniciando infraestructura...")
        results.styles.display = "none"
        buttons.styles.display = "none"

    @work(thread=True)
    def run_deployment_worker(self) -> None:
        """Run ``deploy_vm`` off the UI thread, reporting progress and result."""
        state = self.app.state  # type: ignore[attr-defined]
        provider = self._get_provider()

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
        self._deploying = False
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

        self._arm_session_guard()
        self.call_after_refresh(self._show_tunnel)

    def _show_tunnel(self) -> None:
        """Replace this screen with the live tunnel view.

        Reached via ``call_after_refresh`` so the success state is rendered
        before the swap, and never during layout.
        """
        self.app.switch_screen(TunnelScreen())

    def _arm_session_guard(self) -> None:
        """Make the running tunnel survive an unexpected exit.

        Writes the on-disk marker and attaches a teardown to the session guard,
        so quitting, ``Ctrl+C``, a POSIX signal or interpreter exit all release
        the tunnel and the cloud resources. The guard is idempotent: whichever
        trigger fires first performs the teardown and the rest are no-ops.

        The teardown deliberately references only the app, never ``self``: by the
        time it runs this screen has usually been swapped for the tunnel view, and
        a closure over a discarded screen would fail to report progress.
        """
        state = self.app.state
        app = self.app
        provider_name = state.provider_name
        region = state.selected_region

        write_active_session(provider_name, region)

        def teardown(reason: str) -> None:
            """Release the session's resources.

            Args:
                reason (str): Why the session is shutting down.
            """
            report = app.thread_safe_call
            report(f"Destruyendo el túnel ({reason})...")
            teardown_active_session(
                provider_name,
                region,
                on_progress=lambda msg, _p: report(msg),
            )

        state.session_guard.arm(teardown)

    def _handle_error(self, error_msg: str) -> None:
        self._deploying = False
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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-progress-back":
            self.action_back()
        elif event.button.id == "btn-progress-destroy":
            self._confirm_then_destroy()

    def _confirm_then_destroy(self) -> None:
        """Tear the VPN down from the results view, asking first like the
        tunnel view does (ConfirmDestroyScreen) unless ``confirm_destroy`` was
        disabled. Either way the teardown goes through ``request_shutdown``, so
        it runs the armed session guard — there is exactly one destroy path."""
        state = self.app.state  # type: ignore[attr-defined]
        if state.config.confirm_destroy:
            self.app.push_screen(ConfirmDestroyScreen(), self._on_destroy_choice)
        else:
            request_shutdown(self.app, "destroy requested from the progress screen")

    def _on_destroy_choice(self, choice: tuple[bool, bool] | None) -> None:
        """Apply the destroy modal's verdict from the results view."""
        if choice is None or not choice[0]:
            return

        _, no_ask = choice
        if no_ask:
            state = self.app.state  # type: ignore[attr-defined]
            state.config.confirm_destroy = False
            try:
                save_session_config(state.config)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Could not persist confirm_destroy: {exc}")

        request_shutdown(self.app, "destroy confirmed from the progress screen")

    def action_back(self) -> None:
        """Leave the progress screen, only when nothing is in flight.

        Popping while ``deploy_vm`` is still running would leave the worker
        calling into a discarded screen: the resources could come up with no
        guard armed and no marker written, which is exactly the invisible orphan
        this design exists to prevent. ``q``/``Ctrl+C`` remain available and route
        through the session guard, so the user is never trapped.
        """
        if self._deploying:
            try:
                self.query_one("#progress-status-msg", Static).update(
                    "Espera a que termine el despliegue "
                    "(q / Ctrl+C para salir y destruir)."
                )
            except Exception:
                pass
            return

        # Return to main menu screen
        self.app.pop_screen()
        # If deploy screen was also pushed, pop it to return to main menu
        if (
            len(self.app.screen_stack) > 1
            and type(self.app.screen).__name__ == "DeployScreen"
        ):
            self.app.pop_screen()
