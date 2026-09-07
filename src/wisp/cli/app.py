"""Root Textual application and themes for Wisp CLI."""

from textual.app import App
from textual.binding import Binding

from wisp.cli.screens import ConfigScreen, DeployScreen, MainMenuScreen
from wisp.cli.state import AppState


class WispApp(App):
    """The Wisp terminal UI application with dual themes (Zinc & Amber)."""

    TITLE = "wisp"
    SUB_TITLE = "ephemeral wireguard vpns"

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("ctrl+c", "quit", "Quit", show=False),
    ]

    CSS = """
    /* =========================================================================
       BASE LAYOUT (ZERO-SCROLL VIEWPORT)
       ========================================================================= */
    Screen {
        layout: vertical;
        padding: 0;
        margin: 0;
        width: 100%;
        height: 100%;
    }

    Header {
        dock: top;
        height: 1;
    }

    Footer {
        dock: bottom;
        height: 1;
    }

    .app-top-bar {
        height: 3;
        width: 100%;
        layout: horizontal;
        align: left middle;
        padding: 0 2;
    }

    .breadcrumb {
        width: 1fr;
        layout: horizontal;
        align: left middle;
    }

    .top-badges {
        width: auto;
        layout: horizontal;
        align: right middle;
    }

    .top-badges Static {
        margin-left: 1;
    }

    .split-layout {
        layout: horizontal;
        width: 100%;
        height: 1fr;
    }

    .sidebar {
        width: 28;
        min-width: 26;
        height: 100%;
        layout: vertical;
        padding: 1 1;
        overflow-y: hidden;
    }

    .main-workspace {
        width: 1fr;
        height: 100%;
        layout: vertical;
        padding: 1 2;
        overflow-y: hidden;
    }

    .sidebar-section-title {
        text-style: bold;
        margin-top: 0;
        margin-bottom: 1;
    }

    .context-box {
        padding: 1;
        margin-top: 1;
        layout: vertical;
    }

    .context-box Static {
        margin-bottom: 0;
    }

    /* Cards inside workspace */
    .workspace-card {
        padding: 1 2;
        margin-bottom: 1;
        layout: vertical;
        height: auto;
    }

    .card-header-row {
        layout: horizontal;
        align: left middle;
        width: 100%;
        margin-bottom: 1;
    }

    .card-header-row Static {
        width: 1fr;
    }

    .metric-row {
        layout: horizontal;
        width: 100%;
        margin-top: 0;
        margin-bottom: 1;
    }

    .metric-chip {
        padding: 1;
        width: 1fr;
        height: auto;
        layout: vertical;
        margin-right: 1;
    }

    .grid-2col {
        layout: horizontal;
        width: 100%;
        height: auto;
    }

    .grid-col {
        width: 1fr;
        layout: vertical;
        margin-right: 2;
        height: auto;
    }

    .grid-3col {
        layout: horizontal;
        width: 100%;
        height: auto;
    }

    .grid-col3 {
        width: 1fr;
        layout: vertical;
        margin-right: 1;
        height: auto;
    }

    .callout-action-box {
        padding: 0 2;
        margin-top: 1;
        layout: horizontal;
        align: left middle;
        width: 100%;
        height: 3;
    }

    .callout-action-box .callout-text {
        width: 1fr;
    }

    .callout-action-box .callout-key {
        width: auto;
    }

    OptionList {
        background: transparent;
        border: none;
        height: auto;
        padding: 0;
        margin-bottom: 1;
    }

    OptionList:focus {
        border: none;
    }

    .field-card {
        padding: 1;
        margin-bottom: 1;
        layout: vertical;
        height: auto;
    }

    .field-top-row {
        layout: horizontal;
        align: left middle;
        width: 100%;
    }

    .btn-group {
        height: 3;
        margin-top: 1;
        layout: horizontal;
        width: 100%;
    }

    .btn-group Button {
        margin-right: 1;
        width: 1fr;
    }

    Button {
        height: 3;
    }

    ProgressBar {
        width: 100%;
        margin-top: 1;
        margin-bottom: 1;
    }

    /* =========================================================================
       THEME: MONOCHROMATIC ZINC (DEFAULT)
       ========================================================================= */
    Screen, .theme-zinc Screen {
        background: #0c0c0e;
        color: #f4f4f5;
    }

    Header, .theme-zinc Header {
        background: #111114;
        color: #e4e4e7;
        border-bottom: solid #27272a;
    }

    Footer, .theme-zinc Footer {
        background: #111114;
        color: #a1a1aa;
        border-top: solid #27272a;
    }

    .app-top-bar, .theme-zinc .app-top-bar {
        background: #0c0c0e;
        border-bottom: solid #27272a;
    }

    .sidebar, .theme-zinc .sidebar {
        background: #111114;
        border-right: solid #27272a;
    }

    .sidebar-section-title, .theme-zinc .sidebar-section-title {
        color: #52525b;
    }

    .main-workspace, .theme-zinc .main-workspace {
        background: #0c0c0e;
    }

    .workspace-card, .theme-zinc .workspace-card {
        background: #141418;
        border: solid #27272a;
    }

    .context-box, .theme-zinc .context-box {
        background: #16161a;
        border: solid #27272a;
    }

    .metric-chip, .theme-zinc .metric-chip {
        background: #111114;
        border: solid #27272a;
    }

    .callout-action-box, .theme-zinc .callout-action-box {
        background: #18181b;
        border: solid #3f3f46;
    }

    OptionList > .option-list--option-highlighted,
    .theme-zinc OptionList > .option-list--option-highlighted {
        background: #27272a;
        color: #ffffff;
        text-style: bold;
    }

    .field-card, .theme-zinc .field-card {
        background: #141418;
        border: solid #27272a;
    }

    Input, .theme-zinc Input {
        background: #111114;
        border: tall #27272a;
        color: #f4f4f5;
    }

    Input:focus, .theme-zinc Input:focus {
        border: tall #71717a;
    }

    Select, .theme-zinc Select {
        background: #111114;
        border: tall #27272a;
    }

    Select:focus, .theme-zinc Select:focus {
        border: tall #71717a;
    }

    Button, .theme-zinc Button {
        background: #27272a;
        color: #f4f4f5;
        border: tall #3f3f46;
    }

    Button:hover, .theme-zinc Button:hover {
        background: #3f3f46;
        border: tall #71717a;
    }

    Button.-primary, .theme-zinc Button.-primary {
        background: #3f3f46;
        color: #ffffff;
        border: tall #a1a1aa;
    }

    Button.-primary:hover, .theme-zinc Button.-primary:hover {
        background: #52525b;
    }

    Button.-error, .theme-zinc Button.-error {
        background: #7f1d1d;
        color: #ffffff;
        border: tall #ef4444;
    }

    /* =========================================================================
       THEME: WARM AMBER PHOSPHOR
       ========================================================================= */
    .theme-amber Screen {
        background: #0a0b0e;
        color: #fef3c7;
    }

    .theme-amber Header {
        background: #0f1117;
        color: #f59e0b;
        border-bottom: solid #222634;
    }

    .theme-amber Footer {
        background: #0f1117;
        color: #9ca3af;
        border-top: solid #222634;
    }

    .theme-amber .app-top-bar {
        background: #0a0b0e;
        border-bottom: solid #222634;
    }

    .theme-amber .sidebar {
        background: #0f1117;
        border-right: solid #222634;
    }

    .theme-amber .sidebar-section-title {
        color: #4b5563;
    }

    .theme-amber .main-workspace {
        background: #0a0b0e;
    }

    .theme-amber .workspace-card {
        background: #141722;
        border: solid #222634;
    }

    .theme-amber .context-box {
        background: #141722;
        border: solid #222634;
    }

    .theme-amber .metric-chip {
        background: #121318;
        border: solid #222634;
    }

    .theme-amber .callout-action-box {
        background: #201402;
        border: solid #92400e;
    }

    .theme-amber OptionList > .option-list--option-highlighted {
        background: #291b04;
        color: #f59e0b;
        text-style: bold;
    }

    .theme-amber .field-card {
        background: #141722;
        border: solid #222634;
    }

    .theme-amber Input {
        background: #0f1117;
        border: tall #222634;
        color: #fef3c7;
    }

    .theme-amber Input:focus {
        border: tall #f59e0b;
    }

    .theme-amber Select {
        background: #0f1117;
        border: tall #222634;
    }

    .theme-amber Select:focus {
        border: tall #f59e0b;
    }

    .theme-amber Button {
        background: #1c1304;
        color: #f59e0b;
        border: tall #78350f;
    }

    .theme-amber Button:hover {
        background: #291b04;
        border: tall #f59e0b;
    }

    .theme-amber Button.-primary {
        background: #f59e0b;
        color: #1c1102;
        border: tall #fbbf24;
    }

    .theme-amber Button.-primary:hover {
        background: #d97706;
    }

    .theme-amber Button.-error {
        background: #7f1d1d;
        color: #ffffff;
        border: tall #ef4444;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.state = AppState()

    def on_mount(self) -> None:
        """Install screens and apply the configured visual theme."""
        self.apply_theme()
        self.install_screen(MainMenuScreen(), name="main_menu")
        self.install_screen(ConfigScreen(), name="config")
        self.install_screen(DeployScreen(), name="deploy")
        self.push_screen("main_menu")

    def apply_theme(self) -> None:
        """Apply theme class to root app based on state."""
        theme = getattr(self.state.config, "theme", "zinc")
        if theme == "amber":
            self.remove_class("theme-zinc")
            self.add_class("theme-amber")
        else:
            self.remove_class("theme-amber")
            self.add_class("theme-zinc")
