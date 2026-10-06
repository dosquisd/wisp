"""Configuration screen: edit the in-memory session :class:`WispConfig` and
inspect (read-only) the resolved provider credentials.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import CenterMiddle, Horizontal, Vertical
from textual.widgets import (
    Button,
    Collapsible,
    Footer,
    Header,
    Input,
    Label,
    Static,
    Switch,
)

from wisp.cli.screens.base import WispScreen
from wisp.config.settings import describe_config_sources, save_session_config


def _mask(value: str, keep: int = 4) -> str:
    """Mask a secret, keeping only its last few characters visible."""
    if not value:
        return "[dim]— no configurado —[/dim]"
    if len(value) <= keep:
        return "•" * len(value)
    return "•" * (len(value) - keep) + value[-keep:]


def _cred_line(label: str, value: str, *, sensitive: bool, revealed: bool) -> str:
    """Render one ``label: value`` line, masking sensitive values by default."""
    if not sensitive:
        shown = value if value else "[dim]— default —[/dim]"
    else:
        shown = value if revealed else _mask(value)
    return f"[dim]{label}:[/dim] {shown}"


class ConfigScreen(WispScreen):
    """Form to edit session config in memory, with inline validation."""

    BINDINGS = [
        Binding("escape", "back", "Volver", show=True),
    ]

    CSS = """
    #form-container {
        height: auto;
        margin-bottom: 1;
    }

    #config-source-note {
        margin-bottom: 1;
    }

    #form-container Label {
        color: #94a3b8;
    }

    #switch-row {
        height: 3;
        align: left middle;
        margin-top: 1;
        margin-bottom: 1;
    }

    #switch-row Label {
        margin-top: 0;
        margin-right: 2;
    }

    #credentials-heading {
        margin-top: 0;
    }

    #credentials-section {
        height: auto;
    }

    ConfigScreen .subtitle {
        margin-bottom: 0;
    }

    ConfigScreen .title {
        margin-bottom: 0;
    }

    Collapsible {
        margin-bottom: 0;
    }

    Collapsible Label {
        color: #94a3b8;
    }

    Collapsible Input {
        margin-bottom: 1;
    }

    .cred-reveal-row {
        height: 3;
        align: left middle;
        margin-top: 1;
    }

    .cred-reveal-row Label {
        margin-top: 0;
        margin-right: 2;
    }

    .btn-group {
        height: 3;
        margin-top: 1;
    }

    .btn-group Button {
        margin-right: 1;
        width: 1fr;
    }

    #error-message {
        color: #ef4444;
        text-align: center;
        height: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with CenterMiddle():
            with Vertical(classes="card"):
                yield Static(
                    "[bold cyan]Configuración de Sesión[/bold cyan]", classes="title"
                )
                yield Static(
                    "Modifica los parámetros para los despliegues de esta sesión.",
                    classes="subtitle",
                )
                yield Static(describe_config_sources(), id="config-source-note")

                with Vertical(id="form-container"):
                    yield Label("Timeout VM Boot (segundos para boot):")
                    yield Input(
                        id="input-vm-boot-timeout",
                        value=str(self.app.state.config.vm_boot_timeout),
                        type="integer",
                    )

                    yield Label("Puerto WireGuard (0 = aleatorio 49152-65535):")
                    yield Input(
                        id="input-wireguard-port",
                        value=str(self.app.state.config.wireguard_port),
                        type="integer",
                    )

                    yield Label("Interfaz de WireGuard:")
                    yield Input(
                        id="input-wireguard-interface",
                        value=self.app.state.config.wireguard_interface,
                    )

                    yield Label("DNS Primario:")
                    yield Input(
                        id="input-dns1",
                        value=self.app.state.config.wireguard_dns1,
                    )

                    yield Label("DNS Secundario:")
                    yield Input(
                        id="input-dns2",
                        value=self.app.state.config.wireguard_dns2,
                    )

                    with Horizontal(id="switch-row"):
                        yield Label("Restringir acceso solo a mi IP pública:")
                        yield Switch(
                            id="switch-force-ip",
                            value=self.app.state.config.force_current_ip,
                        )

                yield Static(
                    "[bold]Credenciales[/bold] [dim](solo lectura — desde wisp.toml "
                    "o env)[/dim]",
                    id="credentials-heading",
                    classes="subtitle",
                )
                with Vertical(id="credentials-section"):
                    with Collapsible(
                        title=self._aws_cred_title(),
                        collapsed=True,
                        id="cred-aws-collapsible",
                    ):
                        yield Label("Región (editable — se guarda en wisp.toml):")
                        yield Input(
                            id="input-aws-region",
                            value=self.app.state.aws_credentials.region,
                            placeholder="p.ej. us-east-2",
                        )
                        yield Static(
                            self._aws_cred_text(revealed=False), id="aws-cred-text"
                        )
                        with Horizontal(classes="cred-reveal-row"):
                            yield Label("Mostrar valores completos:")
                            yield Switch(id="switch-reveal-aws", value=False)

                    with Collapsible(
                        title=self._oci_cred_title(),
                        collapsed=True,
                        id="cred-oci-collapsible",
                    ):
                        yield Label("Región (editable — se guarda en wisp.toml):")
                        yield Input(
                            id="input-oci-region",
                            value=self.app.state.oci_credentials.region,
                            placeholder="p.ej. us-ashburn-1",
                        )
                        yield Static(
                            self._oci_cred_text(revealed=False), id="oci-cred-text"
                        )
                        with Horizontal(classes="cred-reveal-row"):
                            yield Label("Mostrar valores completos:")
                            yield Switch(id="switch-reveal-oci", value=False)

                    with Collapsible(
                        title=self._gcp_cred_title(),
                        collapsed=True,
                        id="cred-gcp-collapsible",
                    ):
                        yield Label("Región (editable — se guarda en wisp.toml):")
                        yield Input(
                            id="input-gcp-region",
                            value=self.app.state.gcp_credentials.region,
                            placeholder="p.ej. us-central1",
                        )
                        yield Static(
                            self._gcp_cred_text(revealed=False), id="gcp-cred-text"
                        )
                        with Horizontal(classes="cred-reveal-row"):
                            yield Label("Mostrar valores completos:")
                            yield Switch(id="switch-reveal-gcp", value=False)

                yield Static("", id="error-message")

                with Horizontal(classes="btn-group"):
                    yield Button(
                        "Guardar",
                        id="btn-save",
                        variant="primary",
                        classes="btn-primary",
                    )
                    yield Button(
                        "Restablecer",
                        id="btn-reset",
                        variant="default",
                        classes="btn-secondary",
                    )
                    yield Button(
                        "Volver",
                        id="btn-back",
                        variant="default",
                        classes="btn-secondary",
                    )
        yield Footer()

    # ─── Credentials (read-only, masked) ──────────────────────────

    def _aws_cred_title(self) -> str:
        creds = self.app.state.aws_credentials
        status = "Configurado" if creds.is_explicitly_configured() else "Auto-detectado"
        return f"AWS — {status}"

    def _oci_cred_title(self) -> str:
        creds = self.app.state.oci_credentials
        status = "Configurado" if creds.is_explicitly_configured() else "Auto-detectado"
        return f"OCI — {status}"

    def _gcp_cred_title(self) -> str:
        creds = self.app.state.gcp_credentials
        if creds.is_explicitly_configured():
            return "GCP — Configurado"
        return "GCP — Auto-detectado (ADC)"

    def _aws_cred_text(self, revealed: bool) -> str:
        creds = self.app.state.aws_credentials
        return "\n".join(
            [
                _cred_line("Perfil", creds.profile, sensitive=False, revealed=revealed),
                _cred_line(
                    "Access Key ID",
                    creds.access_key_id,
                    sensitive=True,
                    revealed=revealed,
                ),
                _cred_line(
                    "Secret Access Key",
                    creds.secret_access_key,
                    sensitive=True,
                    revealed=revealed,
                ),
                _cred_line(
                    "Session Token",
                    creds.session_token,
                    sensitive=True,
                    revealed=revealed,
                ),
            ]
        )

    def _oci_cred_text(self, revealed: bool) -> str:
        creds = self.app.state.oci_credentials
        return "\n".join(
            [
                _cred_line(
                    "Tenancy OCID",
                    creds.tenancy_ocid,
                    sensitive=True,
                    revealed=revealed,
                ),
                _cred_line(
                    "User OCID", creds.user_ocid, sensitive=True, revealed=revealed
                ),
                _cred_line(
                    "Fingerprint", creds.fingerprint, sensitive=True, revealed=revealed
                ),
                _cred_line(
                    "Private Key Path",
                    creds.private_key_path,
                    sensitive=False,
                    revealed=revealed,
                ),
                _cred_line(
                    "Compartment OCID",
                    creds.get_compartment_ocid(),
                    sensitive=True,
                    revealed=revealed,
                ),
                _cred_line("Perfil", creds.profile, sensitive=False, revealed=revealed),
            ]
        )

    def _gcp_cred_text(self, revealed: bool) -> str:
        creds = self.app.state.gcp_credentials
        return "\n".join(
            [
                _cred_line(
                    "Project ID", creds.project_id, sensitive=False, revealed=revealed
                ),
                _cred_line("Región", creds.region, sensitive=False, revealed=revealed),
                _cred_line(
                    "Zona", creds.get_zone(), sensitive=False, revealed=revealed
                ),
                _cred_line(
                    "Credentials Path",
                    creds.credentials_path,
                    sensitive=False,
                    revealed=revealed,
                ),
            ]
        )

    def on_switch_changed(self, event: Switch.Changed) -> None:
        if event.switch.id == "switch-reveal-aws":
            self.query_one("#aws-cred-text", Static).update(
                self._aws_cred_text(revealed=event.value)
            )
        elif event.switch.id == "switch-reveal-oci":
            self.query_one("#oci-cred-text", Static).update(
                self._oci_cred_text(revealed=event.value)
            )
        elif event.switch.id == "switch-reveal-gcp":
            self.query_one("#gcp-cred-text", Static).update(
                self._gcp_cred_text(revealed=event.value)
            )

    # ─── General settings form ────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self.save_config()
        elif event.button.id == "btn-reset":
            self.reset_config()
        elif event.button.id == "btn-back":
            self.action_back()

    def save_config(self) -> None:
        """Validate the form and, if valid, persist it to ``AppState`` *and*
        to the active ``wisp.toml`` (see :func:`save_session_config`).

        Shows an inline error and returns early if any field is invalid
        (timeout < 5, port out of ``0-65535``, empty interface/DNS). Nothing
        is written to disk until the whole form passes validation — changes
        are staged in the widgets until this one confirm step.
        """
        timeout_raw = self.query_one("#input-vm-boot-timeout", Input).value.strip()
        port_raw = self.query_one("#input-wireguard-port", Input).value.strip()
        interface = self.query_one("#input-wireguard-interface", Input).value.strip()
        dns1 = self.query_one("#input-dns1", Input).value.strip()
        dns2 = self.query_one("#input-dns2", Input).value.strip()
        force_ip = self.query_one("#switch-force-ip", Switch).value
        aws_region = self.query_one("#input-aws-region", Input).value.strip()
        oci_region = self.query_one("#input-oci-region", Input).value.strip()
        gcp_region = self.query_one("#input-gcp-region", Input).value.strip()

        error_label = self.query_one("#error-message", Static)

        try:
            timeout_val = int(timeout_raw)
            if timeout_val < 5:
                error_label.update("[!] El timeout debe ser de al menos 5 segundos.")
                return
        except ValueError:
            error_label.update("[!] El timeout debe ser un número entero.")
            return

        try:
            port_val = int(port_raw)
            if port_val < 0 or port_val > 65535:
                error_label.update("[!] El puerto debe estar entre 0 y 65535.")
                return
        except ValueError:
            error_label.update("[!] El puerto debe ser un número entero.")
            return

        if not interface:
            error_label.update("[!] La interfaz WireGuard no puede estar vacía.")
            return

        if not dns1 or not dns2:
            error_label.update("[!] Los servidores DNS no pueden estar vacíos.")
            return

        # Update in-memory state
        state = self.app.state
        state.config.vm_boot_timeout = timeout_val
        state.config.wireguard_port = port_val
        state.config.wireguard_interface = interface
        state.config.wireguard_dns1 = dns1
        state.config.wireguard_dns2 = dns2
        state.config.force_current_ip = force_ip

        # Persist to disk: [general] fully, plus just the `region` key of
        # [aws]/[oci]/[gcp] — everything else in those sections (credentials,
        # profile, etc.) is left untouched, since this form never edits them.
        try:
            target_path = save_session_config(
                state.config,
                provider_regions={
                    "aws": aws_region,
                    "oci": oci_region,
                    "gcp": gcp_region,
                },
            )
        except Exception as exc:  # e.g. tomli-w missing, permissions, disk full
            error_label.update(f"[!] No se pudo guardar en disco: {exc}")
            return

        # Regions may have changed what's "explicitly configured" for each
        # provider, so re-resolve credentials and refresh the collapsibles
        # to match — and reset the reveal toggles as a safe default.
        state.refresh_credentials()
        self._refresh_credentials_ui()

        self.notify(f"Configuración guardada en {target_path}", severity="information")
        self.app.pop_screen()

    def _refresh_credentials_ui(self) -> None:
        """Re-render the credentials collapsibles from freshly resolved state."""
        try:
            self.query_one(
                "#cred-aws-collapsible", Collapsible
            ).title = self._aws_cred_title()
            self.query_one("#aws-cred-text", Static).update(
                self._aws_cred_text(revealed=False)
            )
            self.query_one("#switch-reveal-aws", Switch).value = False

            self.query_one(
                "#cred-oci-collapsible", Collapsible
            ).title = self._oci_cred_title()
            self.query_one("#oci-cred-text", Static).update(
                self._oci_cred_text(revealed=False)
            )
            self.query_one("#switch-reveal-oci", Switch).value = False

            self.query_one(
                "#cred-gcp-collapsible", Collapsible
            ).title = self._gcp_cred_title()
            self.query_one("#gcp-cred-text", Static).update(
                self._gcp_cred_text(revealed=False)
            )
            self.query_one("#switch-reveal-gcp", Switch).value = False
        except Exception:
            pass

    def reset_config(self) -> None:
        """Reset the session config to what's in ``wisp.toml`` and repopulate
        the form from that reloaded config (not from hardcoded defaults —
        see note below)."""
        state = self.app.state
        state.reset_config()

        # NOTE: previously this repopulated the form from a bare
        # WispConfig() (i.e. hardcoded constant defaults), which drifted
        # from what state.reset_config() actually loaded whenever wisp.toml
        # overrides any [general] value. Reading back from state.config
        # keeps the form and the in-memory state in sync.
        cfg = state.config
        self.query_one("#input-vm-boot-timeout", Input).value = str(cfg.vm_boot_timeout)
        self.query_one("#input-wireguard-port", Input).value = str(cfg.wireguard_port)
        self.query_one(
            "#input-wireguard-interface", Input
        ).value = cfg.wireguard_interface
        self.query_one("#input-dns1", Input).value = cfg.wireguard_dns1
        self.query_one("#input-dns2", Input).value = cfg.wireguard_dns2
        self.query_one("#switch-force-ip", Switch).value = cfg.force_current_ip

        # Also discard any unsaved edits to the provider region fields,
        # reverting them to whatever is currently resolved (not necessarily
        # what's on disk, if credentials were just refreshed elsewhere).
        self.query_one("#input-aws-region", Input).value = state.aws_credentials.region
        self.query_one("#input-oci-region", Input).value = state.oci_credentials.region
        self.query_one("#input-gcp-region", Input).value = state.gcp_credentials.region

        self.query_one("#error-message", Static).update("")
        self.notify("Configuración restablecida desde wisp.toml", severity="warning")

    def on_screen_resume(self) -> None:
        # Textual focuses the first Input before the first layout pass, so
        # the scroll_visible() it triggers computes against pre-layout
        # dimensions and leaves the card scrolled even when the input was
        # already in view (the title ends up cut off). Re-anchor the scroll
        # once the layout settles.
        self.call_after_refresh(self.query_one(".card").scroll_to, y=0, animate=False)

    def action_back(self) -> None:
        self.app.pop_screen()
