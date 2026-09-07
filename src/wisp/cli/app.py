"""Root Textual application and global styles for the Wisp TUI."""

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
    SUB_TITLE = "ephemeral wireguard vpns"

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("ctrl+c", "quit", "Quit", show=False),
    ]

    CSS = """
    Screen {
        background: #090d16;
        color: #f8fafc;
        align: center middle;
    }

    Header {
        background: #090d16;
        color: #38bdf8;
        dock: top;
        height: 1;
        border-bottom: solid #1e293b;
    }

    Footer {
        background: #090d16;
        dock: bottom;
        height: 1;
        border-top: solid #1e293b;
    }

    .card {
        background: #0f172a;
        border: round #334155;
        padding: 1 2;
        width: 76;
        height: auto;
        max-height: 96%;
        overflow-y: auto;
    }

    .card:focus-within {
        border: round #38bdf8;
    }

    .cli-brand {
        text-align: center;
        color: #38bdf8;
        text-style: bold;
        margin-bottom: 1;
    }

    .cli-tagline {
        text-align: center;
        color: #64748b;
        margin-bottom: 1;
    }

    .status-panel {
        background: #090d16;
        border: solid #1e293b;
        padding: 0 1;
        margin-bottom: 1;
    }

    OptionList {
        background: transparent;
        border: none;
        height: auto;
        margin-top: 1;
        margin-bottom: 1;
        padding: 0;
    }

    OptionList:focus {
        border: none;
    }

    OptionList > .option-list--option-highlighted {
        background: #1e293b;
        color: #38bdf8;
        text-style: bold;
    }

    .btn-group {
        height: 3;
        margin-top: 1;
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
