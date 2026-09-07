"""Deploy screen: pick provider and region, review, and launch deployment."""

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Select, Static

from wisp.cli.screens.progress import ProgressScreen

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


class DeployScreen(Screen):
    """Provider and region selection wizard with target review."""

    BINDINGS = [
        Binding("escape", "back", "Back", show=True),
        Binding("ctrl+d", "start_deploy", "Deploy", show=True),
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
        background: #090d16;
        border: solid #1e293b;
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
                    "[bold cyan]Deploy WireGuard VPN[/bold cyan]",
                    classes="cli-brand",
                )
                yield Static(
                    "Select cloud provider and target region to provision an ephemeral VPN.",
                    classes="cli-tagline",
                )

                with Vertical(id="deploy-container"):
                    yield Label("1. Cloud Provider:")
                    yield Select(
                        options=[("Amazon Web Services (AWS)", "aws")],
                        value="aws",
                        allow_blank=False,
                        id="select-provider",
                    )

                    yield Label("2. Deployment Region:")
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
                        "[dim]Syncing available regions with AWS...[/dim]",
                        id="region-status",
                    )

                    yield Label("3. Deployment Target Summary:")
                    yield Static(
                        self._build_summary(current_region), id="deploy-summary"
                    )

                with Horizontal(classes="btn-group"):
                    yield Button(
                        "Launch Deployment",
                        id="btn-start-deploy",
                        variant="primary",
                    )
                    yield Button(
                        "Cancel",
                        id="btn-cancel",
                        variant="default",
                    )
        yield Footer()

    def on_mount(self) -> None:
        self.fetch_live_regions()

    def on_screen_resume(self) -> None:
        region_select = self.query_one("#select-region", Select)
        current = str(region_select.value)
        self.query_one("#deploy-summary", Static).update(
            self._build_summary(current)
        )

    @work(thread=True)
    def fetch_live_regions(self) -> None:
        """Fetch live AWS regions in a background thread; fall back on error."""
        try:
            from wisp.providers.aws import AWSProvider

            provider = AWSProvider()
            regions = list(provider.get_available_regions())
            if regions:
                self.app.call_from_thread(
                    self._update_regions_ui, sorted(regions)
                )
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
                f"[green]✓ {len(regions)} regions available in AWS[/green]"
            )
            self.query_one("#deploy-summary", Static).update(
                self._build_summary(str(current_val))
            )
        except Exception:
            pass

    def _region_fetch_failed(self) -> None:
        try:
            status = self.query_one("#region-status", Static)
            status.update("[dim](Using standard AWS regions)[/dim]")
        except Exception:
            pass

    def on_select_changed(self, event: Select.Changed) -> None:
        if (
            event.select.id == "select-region"
            and event.value is not Select.BLANK
        ):
            self.query_one("#deploy-summary", Static).update(
                self._build_summary(str(event.value))
            )

    def _build_summary(self, region: str) -> str:
        """Build the deployment summary text for the given region."""
        state = self.app.state  # type: ignore[attr-defined]
        cfg = state.config
        port_text = (
            f"UDP {cfg.wireguard_port}"
            if cfg.wireguard_port > 0
            else "Dynamic (49152-65535)"
        )
        ip_mode = (
            "Current public IP only (/32)"
            if cfg.force_current_ip
            else "Open (0.0.0.0/0)"
        )
        return (
            f"[dim]PROVIDER[/dim]  AWS (Amazon Web Services)   [dim]REGION[/dim]  [yellow]{region}[/yellow]\n"
            f"[dim]TIMEOUT[/dim]   {cfg.ansible_timeout}s                      [dim]PORT[/dim]    {port_text}\n"
            f"[dim]DNS[/dim]       {cfg.wireguard_dns1}, {cfg.wireguard_dns2}      [dim]ACCESS[/dim]  {ip_mode}"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-start-deploy":
            self.start_deployment()
        elif event.button.id == "btn-cancel":
            self.action_back()

    def action_start_deploy(self) -> None:
        self.start_deployment()

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
