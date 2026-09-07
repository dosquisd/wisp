"""Deploy screen: compact wizard to select provider/region and launch."""

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, OptionList, Select, Static
from textual.widgets.option_list import Option

from wisp.cli.screens.progress import ProgressScreen

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
    """Zero-scroll provider and region selection wizard with target review."""

    BINDINGS = [
        Binding("escape", "back", "Back", show=True),
        Binding("ctrl+d", "start_deploy", "Deploy", show=True),
    ]

    def compose(self) -> ComposeResult:
        current_region = self.app.state.selected_region  # type: ignore[attr-defined]
        yield Header(show_clock=True)

        # Top breadcrumb bar
        with Horizontal(classes="app-top-bar"):
            with Horizontal(classes="breadcrumb"):
                yield Static(
                    "[bold white]wisp[/bold white] [dim]›[/dim] [dim]deploy wizard[/dim]"
                )
            with Horizontal(classes="top-badges"):
                yield Static(
                    f"[dim on #18181b] TARGET: {current_region} [/dim on #18181b]",
                    id="top-region-badge",
                )

        # Multi-pane split layout
        with Horizontal(classes="split-layout"):
            # Left Sidebar (compact 28 chars)
            with Vertical(classes="sidebar"):
                yield Static("WIZARD STEPS", classes="sidebar-section-title")
                yield OptionList(
                    Option("✓ 01. Cloud Provider", id="step-1"),
                    Option("› 02. Region Target", id="step-2"),
                    Option("  03. Review & Launch", id="step-3"),
                    id="wizard-steps",
                )

                with Vertical(classes="context-box"):
                    yield Static("[dim]DEPLOY SPEC[/dim]")
                    yield Static("[dim]• Cloud:[/dim] [white]AWS (EC2)[/white]")
                    yield Static(
                        "[dim]• Machine:[/dim] [white]t3.micro (Ubuntu 24.04)[/white]"
                    )
                    yield Static(
                        "[dim]• Est Cost:[/dim] [green]~$0.0104 / hour[/green]"
                    )
                    yield Static(
                        "[dim]• Key Pair:[/dim] [white]ED25519 in-memory[/white]"
                    )

            # Right Main Workspace (Zero-Scroll Viewport)
            with Vertical(classes="main-workspace"):
                with Vertical(classes="workspace-card"):
                    yield Static(
                        "[dim]DEPLOYMENT DESTINATION[/dim]",
                        classes="sidebar-section-title",
                    )

                    # Row: Provider & Region side-by-side
                    with Horizontal(classes="grid-2col"):
                        with Vertical(classes="grid-col"):
                            yield Label("[dim]1. Cloud Provider:[/dim]")
                            yield Select(
                                options=[("Amazon Web Services (AWS)", "aws")],
                                value="aws",
                                allow_blank=False,
                                id="select-provider",
                            )

                        with Vertical(classes="grid-col"):
                            yield Label("[dim]2. Deployment Region:[/dim]")
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

                # Target Summary Box
                with Vertical(classes="workspace-card"):
                    yield Static(
                        "[dim]TARGET SUMMARY & FIREWALL POLICY[/dim]",
                        classes="sidebar-section-title",
                    )
                    yield Static(
                        self._build_summary(current_region), id="deploy-summary"
                    )

                # Action Buttons
                with Horizontal(classes="btn-group"):
                    yield Button(
                        "Launch Deployment (Ctrl+D)",
                        id="btn-start-deploy",
                        variant="primary",
                    )
                    yield Button(
                        "Cancel / Back (Esc)", id="btn-cancel", variant="default"
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
        """Fetch live AWS regions in a background thread; fall back on error."""
        try:
            from wisp.providers.aws import AWSProvider

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
                region_select.value if region_select.value in regions else regions[0]
            )
            region_select.set_options([(r, r) for r in regions])
            region_select.value = current_val

            status = self.query_one("#region-status", Static)
            status.update(f"[green]✓ {len(regions)} regions available in AWS[/green]")
            self.query_one("#deploy-summary", Static).update(
                self._build_summary(str(current_val))
            )
            self.query_one("#top-region-badge", Static).update(
                f"[dim on #18181b] TARGET: {current_val} [/dim on #18181b]"
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
        if event.select.id == "select-region" and event.value is not Select.BLANK:
            self.query_one("#deploy-summary", Static).update(
                self._build_summary(str(event.value))
            )
            self.query_one("#top-region-badge", Static).update(
                f"[dim on #18181b] TARGET: {event.value} [/dim on #18181b]"
            )

    def _build_summary(self, region: str) -> str:
        """Build the deployment summary text for the given region."""
        state = self.app.state  # type: ignore[attr-defined]
        cfg = state.config
        port_text = (
            f"UDP {cfg.wireguard_port}"
            if cfg.wireguard_port > 0
            else "Dynamic random (49152-65535)"
        )
        ip_mode = (
            "Caller public IP only (/32)"
            if cfg.force_current_ip
            else "Open (0.0.0.0/0)"
        )
        return (
            f"[dim]Provider:[/dim] AWS (Amazon Web Services)   [dim]Region:[/dim] [yellow]{region}[/yellow]\n"
            f"[dim]Timeout:[/dim]  {cfg.ansible_timeout}s                      [dim]Port:[/dim]   {port_text}\n"
            f"[dim]DNS:[/dim]      {cfg.wireguard_dns1}, {cfg.wireguard_dns2}      [dim]Access:[/dim] {ip_mode}"
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
