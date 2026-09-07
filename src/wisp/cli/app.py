"""Root Textual application and global full-bleed styles for Wisp CLI."""

from textual.app import App
from textual.binding import Binding

from wisp.cli.screens import ConfigScreen, DeployScreen, MainMenuScreen
from wisp.cli.state import AppState


class WispApp(App):
    """The Wisp terminal UI application.

    Owns the shared :class:`~wisp.cli.state.AppState`, defines global CSS and
    key bindings, and installs the main-menu, config, and deploy screens on
    mount.
    """

    TITLE = "wisp"
    SUB_TITLE = "ephemeral wireguard vpns on your cloud"

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("ctrl+c", "quit", "Quit", show=False),
    ]

    CSS = """
    Screen {
        background: #090d16;
        color: #f8fafc;
        layout: vertical;
        padding: 0;
        margin: 0;
        width: 100%;
        height: 100%;
    }

    Header {
        background: #0c101c;
        color: #38bdf8;
        dock: top;
        height: 1;
        border-bottom: solid #1e293b;
    }

    Footer {
        background: #0c101c;
        dock: bottom;
        height: 1;
        border-top: solid #1e293b;
    }

    /* Full-bleed application top bar */
    .app-top-bar {
        height: 3;
        width: 100%;
        background: #090d16;
        border-bottom: solid #1e293b;
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

    /* Full-bleed multi-pane split layout */
    .split-layout {
        layout: horizontal;
        width: 100%;
        height: 1fr;
        background: #090d16;
    }

    .sidebar {
        width: 36;
        min-width: 32;
        height: 100%;
        layout: vertical;
        background: #0a0e19;
        border-right: solid #1e293b;
        padding: 1 2;
        overflow-y: auto;
    }

    .main-workspace {
        width: 1fr;
        height: 100%;
        layout: vertical;
        background: #0e1424;
        padding: 1 2;
        overflow-y: auto;
    }

    /* Section headers */
    .sidebar-section-title {
        color: #64748b;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 1;
    }

    /* Status panel & context box */
    .context-box {
        background: #0c111e;
        border: solid #1e293b;
        padding: 1;
        margin-top: 1;
        layout: vertical;
    }

    .context-box Static {
        margin-bottom: 1;
    }

    /* Cards inside workspace */
    .workspace-card {
        background: #131b2e;
        border: solid #1e293b;
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
        margin-top: 1;
        margin-bottom: 1;
    }

    .metric-chip {
        background: #090d18;
        border: solid #1e293b;
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

    /* Highlighted callout action box */
    .callout-action-box {
        background: #0a1c29;
        border: solid #38bdf8;
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

    /* OptionList navigation */
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

    OptionList > .option-list--option-highlighted {
        background: #152238;
        color: #38bdf8;
        text-style: bold;
    }

    /* Badges */
    .badge-green {
        background: #06281c;
        color: #10b981;
        border: solid #10b981;
        padding: 0 1;
        text-style: bold;
    }

    .badge-cyan {
        background: #10192e;
        color: #38bdf8;
        border: solid #38bdf8;
        padding: 0 1;
        text-style: bold;
    }

    .badge-amber {
        background: #261c06;
        color: #f59e0b;
        border: solid #f59e0b;
        padding: 0 1;
        text-style: bold;
    }

    .badge-red {
        background: #260606;
        color: #ef4444;
        border: solid #ef4444;
        padding: 0 1;
        text-style: bold;
    }

    /* Form styling */
    .field-card {
        background: #0b101c;
        border: solid #1e293b;
        padding: 1 2;
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
        background: #1e293b;
        color: #f8fafc;
        border: tall #334155;
        height: 3;
    }

    Button:hover {
        background: #334155;
        border: tall #38bdf8;
    }

    Button.-primary {
        background: #0284c7;
        color: #ffffff;
        border: tall #38bdf8;
    }

    Button.-primary:hover {
        background: #0369a1;
    }

    Button.-error {
        background: #991b1b;
        color: #ffffff;
        border: tall #ef4444;
    }

    Button.-error:hover {
        background: #b91c1c;
    }

    Input {
        background: #090d16;
        border: tall #1e293b;
        color: #f8fafc;
    }

    Input:focus {
        border: tall #38bdf8;
    }

    Select {
        background: #090d16;
        border: tall #1e293b;
    }

    Select:focus {
        border: tall #38bdf8;
    }

    ProgressBar {
        width: 100%;
        margin-top: 1;
        margin-bottom: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.state = AppState()

    def on_mount(self) -> None:
        """Install the app screens and show the main menu."""
        self.install_screen(MainMenuScreen(), name="main_menu")
        self.install_screen(ConfigScreen(), name="config")
        self.install_screen(DeployScreen(), name="deploy")
        self.push_screen("main_menu")
