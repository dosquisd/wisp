from textual.app import App
from textual.binding import Binding

from src.cli.screens import ConfigScreen, MainMenuScreen
from src.cli.state import AppState


class WispApp(App):
    TITLE = "Wisp"
    SUB_TITLE = "Ephemeral WireGuard VPNs on your own cloud"

    BINDINGS = [
        Binding("q", "quit", "Salir", show=True),
        Binding("ctrl+c", "quit", "Salir", show=False),
    ]

    CSS = """
    Screen {
        background: #0b0f19;
        color: #f1f5f9;
        align: center middle;
    }

    Header {
        background: #111827;
        color: #38bdf8;
        dock: top;
        height: 1;
    }

    Footer {
        background: #111827;
        dock: bottom;
        height: 1;
    }

    .card {
        background: #1e293b;
        border: round #38bdf8;
        padding: 1 2;
        width: 72;
        height: auto;
    }

    .title {
        text-style: bold;
        color: #38bdf8;
        text-align: center;
        margin-bottom: 1;
    }

    .subtitle {
        color: #94a3b8;
        text-align: center;
        margin-bottom: 1;
    }

    .btn-primary {
        background: #0284c7;
        color: #ffffff;
        border: none;
        width: 100%;
        margin-top: 1;
    }

    .btn-primary:hover {
        background: #0369a1;
    }

    .btn-secondary {
        background: #334155;
        color: #f8fafc;
        border: none;
        width: 100%;
        margin-top: 1;
    }

    .btn-secondary:hover {
        background: #475569;
    }

    .btn-danger {
        background: #dc2626;
        color: #ffffff;
        border: none;
        width: 100%;
        margin-top: 1;
    }

    .btn-danger:hover {
        background: #b91c1c;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.state = AppState()

    def on_mount(self) -> None:
        self.install_screen(MainMenuScreen(), name="main_menu")
        self.install_screen(ConfigScreen(), name="config")
        self.push_screen("main_menu")
