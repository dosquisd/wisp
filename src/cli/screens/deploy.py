from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Select, Static

FALLBACK_AWS_REGIONS = [
    "us-east-1",
    "us-east-2",
    "us-west-1",
    "us-west-2",
    "eu-west-1",
    "eu-central-1",
    "eu-west-3",
    "ap-southeast-1",
    "ap-northeast-1",
    "sa-east-1",
]


class DeployScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Volver", show=True),
    ]

    CSS = """
    #deploy-container {
        height: auto;
        margin-bottom: 1;
    }

    #deploy-container Label {
        color: #94a3b8;
        margin-top: 1;
    }

    #region-status {
        height: 1;
        margin-top: 0;
        margin-bottom: 1;
    }

    #deploy-summary {
        background: #0b0f19;
        border: solid #334155;
        padding: 0 1;
        margin-top: 1;
        margin-bottom: 1;
        height: auto;
    }

    .btn-group {
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
                    "[bold cyan]Asistente de Despliegue[/bold cyan]", classes="title"
                )
                yield Static(
                    "Selecciona el proveedor y la región para la nueva VPN.",
                    classes="subtitle",
                )

                with Vertical(id="deploy-container"):
                    yield Label("1. Proveedor de Infraestructura:")
                    yield Select(
                        options=[("Amazon Web Services (AWS)", "aws")],
                        value="aws",
                        allow_blank=False,
                        id="select-provider",
                    )

                    yield Label("2. Región de Despliegue:")
                    current_region = self.app.state.selected_region  # type: ignore[attr-defined]
                    regions = (
                        FALLBACK_AWS_REGIONS
                        if current_region in FALLBACK_AWS_REGIONS
                        else [current_region, *FALLBACK_AWS_REGIONS]
                    )
                    yield Select(
                        options=[(r, r) for r in regions],
                        value=current_region,
                        allow_blank=False,
                        id="select-region",
                    )
                    yield Static(
                        "[dim]Sincronizando regiones con AWS...[/dim]",
                        id="region-status",
                    )

                    yield Label("3. Resumen y Confirmación:")
                    yield Static(
                        self._build_summary(current_region), id="deploy-summary"
                    )

                with Horizontal(classes="btn-group"):
                    yield Button(
                        "Iniciar Despliegue",
                        id="btn-start-deploy",
                        variant="primary",
                        classes="btn-primary",
                    )
                    yield Button(
                        "Cancelar",
                        id="btn-cancel",
                        variant="default",
                        classes="btn-secondary",
                    )
        yield Footer()

    def on_mount(self) -> None:
        self.fetch_live_regions()

    def on_screen_resume(self) -> None:
        region_select = self.query_one("#select-region", Select)
        current = str(region_select.value)
        self.query_one("#deploy-summary", Static).update(self._build_summary(current))

    @work(thread=True)
    def fetch_live_regions(self) -> None:
        try:
            from src.providers.aws import AWSProvider

            provider = AWSProvider()
            regions = list(provider.get_available_regions())
            if regions:
                self.app.call_from_thread(self._update_regions_ui, sorted(regions))
        except Exception:
            self.app.call_from_thread(self._region_fetch_failed)

    def _update_regions_ui(self, regions: list[str]) -> None:
        try:
            region_select = self.query_one("#select-region", Select)
            current_val = (
                region_select.value
                if region_select.value in regions
                else regions[0]
            )
            region_select.set_options([(r, r) for r in regions])
            region_select.value = current_val

            status = self.query_one("#region-status", Static)
            status.update(
                f"[green]✓ {len(regions)} regiones disponibles en AWS[/green]"
            )
            self.query_one("#deploy-summary", Static).update(
                self._build_summary(str(current_val))
            )
        except Exception:
            pass

    def _region_fetch_failed(self) -> None:
        try:
            status = self.query_one("#region-status", Static)
            status.update("[dim](Usando lista estándar de regiones AWS)[/dim]")
        except Exception:
            pass

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "select-region" and event.value is not Select.BLANK:
            self.query_one("#deploy-summary", Static).update(
                self._build_summary(str(event.value))
            )

    def _build_summary(self, region: str) -> str:
        state = self.app.state  # type: ignore[attr-defined]
        cfg = state.config
        port_text = (
            f"UDP {cfg.wireguard_port}"
            if cfg.wireguard_port > 0
            else "Aleatorio"
        )
        ip_mode = (
            "Solo tu IP (/32)"
            if cfg.force_current_ip
            else "Cualquier IP (0.0.0.0/0)"
        )
        return (
            f"[cyan]Destino:[/cyan] AWS ({region})   [cyan]Timeout:[/cyan] {cfg.ansible_timeout}s\n"
            f"[cyan]Puerto:[/cyan] {port_text}   [cyan]DNS:[/cyan] {cfg.wireguard_dns1}, {cfg.wireguard_dns2}\n"
            f"[cyan]Firewall:[/cyan] {ip_mode}"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-start-deploy":
            self.start_deployment()
        elif event.button.id == "btn-cancel":
            self.action_back()

    def start_deployment(self) -> None:
        state = self.app.state  # type: ignore[attr-defined]
        provider_val = str(self.query_one("#select-provider", Select).value)
        region_val = str(self.query_one("#select-region", Select).value)

        state.provider_name = provider_val
        state.selected_region = region_val

        self.app.push_screen("progress")

    def action_back(self) -> None:
        self.app.pop_screen()
