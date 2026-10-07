"""Deploy screen: pick provider and region, review, and launch a deployment."""

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import CenterMiddle, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Label, Select, Static

from wisp.cli.screens.base import WispScreen
from wisp.cli.screens.progress import ProgressScreen
from wisp.providers import PROVIDERS_MAP, ProviderEnum
from wisp.providers.base import get_provider_display_name

# Static region list used until live AWS regions are fetched (or if that fails).
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

# Static region list for OCI (fallback)
FALLBACK_OCI_REGIONS = [
    "us-ashburn-1",
    "us-phoenix-1",
    "eu-frankfurt-1",
    "uk-london-1",
    "ap-tokyo-1",
    "ap-sydney-1",
    "ap-seoul-1",
    "ap-mumbai-1",
    "sa-saopaulo-1",
    "ca-toronto-1",
    "eu-zurich-1",
    "me-jeddah-1",
]

# Static region list for GCP (fallback)
FALLBACK_GCP_REGIONS = [
    "us-central1",
    "us-east1",
    "us-west1",
    "europe-west1",
    "europe-west3",
    "asia-east1",
    "asia-southeast1",
    "southamerica-east1",
    "australia-southeast1",
]


class DeployScreen(WispScreen):
    """Provider/region selection with a live deploy summary."""

    BINDINGS = [
        Binding("escape", "back", "Volver", show=True),
    ]

    CSS = """
    /* The deploy card must fit a 24-row terminal without scrolling: a scroll on
       this screen hides exactly what matters — the Start/Cancel buttons. All
       margins here are trimmed hard, and the card padding is dropped, to keep
       the whole card at 18 rows (it was 31). */
    #deploy-card {
        padding: 0 2;
        height: auto;
    }

    #deploy-card .title {
        margin-bottom: 0;
    }

    #deploy-card .subtitle {
        margin-bottom: 0;
    }

    #deploy-container {
        height: auto;
    }

    #deploy-container Label {
        color: #94a3b8;
    }

    #region-status {
        height: 1;
    }

    #deploy-summary {
        background: #0b0f19;
        border: solid #334155;
        padding: 0;
        height: auto;
    }

    .btn-group Button {
        margin-right: 1;
        width: 1fr;
    }

    .btn-group {
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with CenterMiddle():
            with Vertical(classes="card", id="deploy-card"):
                yield Static(
                    "[bold cyan]Asistente de Despliegue[/bold cyan]", classes="title"
                )
                yield Static(
                    "Selecciona el proveedor y la región para la nueva VPN.",
                    classes="subtitle",
                )

                with Vertical(id="deploy-container"):
                    provider_val = self._initial_provider()
                    yield Label("1. Proveedor de Infraestructura:")
                    yield Select(
                        options=[
                            ("Amazon Web Services (AWS)", "aws"),
                            ("Oracle Cloud Infrastructure (OCI)", "oci"),
                            ("Google Cloud Platform (GCP)", "gcp"),
                        ],
                        value=provider_val,
                        allow_blank=False,
                        id="select-provider",
                    )

                    yield Label("2. Región de Despliegue:")
                    current_region = self.app.state.selected_region  # type: ignore[attr-defined]
                    regions = self._get_fallback_regions(provider_val)
                    if current_region in regions:
                        regions = [
                            current_region,
                            *[r for r in regions if r != current_region],
                        ]
                    yield Select(
                        options=[(r, r) for r in regions],
                        value=current_region,
                        allow_blank=False,
                        id="select-region",
                    )
                    yield Static(
                        "[dim]Sincronizando regiones...[/dim]",
                        id="region-status",
                    )

                    yield Label("3. Resumen y Confirmación:")
                    yield Static(
                        self._build_summary(current_region, provider_val),
                        id="deploy-summary",
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

    def _initial_provider(self) -> str:
        """Return the provider to preselect in the provider Select.

        Falls back to ``"aws"`` when the state carries a value the Select has no
        option for, so the widget never starts on a blank selection.
        """
        candidate = str(self.app.state.provider_name)  # type: ignore[attr-defined]
        known = {p.value for p in ProviderEnum}
        return candidate if candidate in known else ProviderEnum.AWS.value

    def _get_fallback_regions(self, provider: str) -> list[str]:
        """Get fallback regions for a provider."""
        if provider == "oci":
            return FALLBACK_OCI_REGIONS
        elif provider == "gcp":
            return FALLBACK_GCP_REGIONS
        return FALLBACK_AWS_REGIONS

    def on_mount(self) -> None:
        self.fetch_live_regions()

    def on_screen_resume(self) -> None:
        region_select = self.query_one("#select-region", Select)
        current = str(region_select.value)
        self.query_one("#deploy-summary", Static).update(
            self._build_summary(current, self._initial_provider())
        )

    @work(thread=True)
    def fetch_live_regions(self) -> None:
        """Fetch live regions for the selected provider in a background thread."""
        provider_val = str(self.query_one("#select-provider", Select).value)
        try:
            provider_cls = PROVIDERS_MAP[ProviderEnum(provider_val)]
            provider = provider_cls()
            regions = list(provider.get_available_regions())
            if regions:
                self.app.call_from_thread(self._update_regions_ui, sorted(regions))
        except Exception:
            self.app.call_from_thread(self._region_fetch_failed)

    def _update_regions_ui(self, regions: list[str]) -> None:
        try:
            region_select = self.query_one("#select-region", Select)
            current_val = (
                region_select.value if region_select.value in regions else regions[0]
            )
            region_select.set_options([(r, r) for r in regions])
            region_select.value = current_val

            provider_val = str(self.query_one("#select-provider", Select).value)
            provider_name = get_provider_display_name(provider_val)
            status = self.query_one("#region-status", Static)
            status.update(
                f"[green]✓ {len(regions)} regiones disponibles en {provider_name}[/green]"
            )
            self.query_one("#deploy-summary", Static).update(
                self._build_summary(str(current_val), provider_val)
            )
        except Exception:
            pass

    def _region_fetch_failed(self) -> None:
        try:
            status = self.query_one("#region-status", Static)
            provider_val = str(self.query_one("#select-provider", Select).value)
            provider_name = get_provider_display_name(provider_val)
            status.update(
                f"[dim](Usando lista estándar de regiones {provider_name})[/dim]"
            )
        except Exception:
            pass

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "select-provider":
            # Provider changed - fetch new regions
            self.fetch_live_regions()
        elif event.select.id == "select-region" and event.value is not Select.BLANK:
            self.query_one("#deploy-summary", Static).update(
                self._build_summary(
                    str(event.value),
                    str(self.query_one("#select-provider", Select).value),
                )
            )

    def _build_summary(self, region: str, provider_val: str) -> str:
        """Build the deployment summary text for the given region.

        The provider is passed in rather than read from the widget: this runs
        during :meth:`compose`, before the Selects exist in the DOM, so querying
        ``#select-provider`` at that point raises ``NoMatches``.

        Args:
            region (str): Region to describe.
            provider_val (str): Selected provider identifier.

        Returns:
            str: Markup for the summary panel.
        """
        state = self.app.state  # type: ignore[attr-defined]
        cfg = state.config
        provider_name = get_provider_display_name(provider_val)
        port_text = (
            f"UDP {cfg.wireguard_port}" if cfg.wireguard_port > 0 else "Aleatorio"
        )
        ip_mode = (
            "Solo tu IP (/32)" if cfg.force_current_ip else "Cualquier IP (0.0.0.0/0)"
        )

        # Credential status
        creds = state.get_credentials_for_provider(provider_val)
        cred_status = (
            "[green]✓ Configurado[/green]"
            if creds and creds.is_explicitly_configured()
            else "[yellow]⚠ Auto-detectado[/yellow]"
        )

        return (
            f"[cyan]Destino:[/cyan] {provider_name} ({region})   [cyan]Timeout:[/cyan] {cfg.vm_boot_timeout}s\n"
            f"[cyan]Puerto:[/cyan] {port_text}   [cyan]DNS:[/cyan] {cfg.wireguard_dns1}, {cfg.wireguard_dns2}\n"
            f"[cyan]Firewall:[/cyan] {ip_mode}   [cyan]Credenciales:[/cyan] {cred_status}"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-start-deploy":
            self.start_deployment()
        elif event.button.id == "btn-cancel":
            self.action_back()

    def start_deployment(self) -> None:
        """Persist the selection into state and push the progress screen."""
        state = self.app.state  # type: ignore[attr-defined]
        provider_val = str(self.query_one("#select-provider", Select).value)
        region_val = str(self.query_one("#select-region", Select).value)

        state.provider_name = provider_val
        state.selected_region = region_val

        self.app.push_screen(ProgressScreen())

    def action_back(self) -> None:
        self.app.pop_screen()
