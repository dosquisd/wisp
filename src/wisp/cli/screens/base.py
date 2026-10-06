"""Shared base screen for the Wisp TUI.

Textual only cycles focus with Tab/Shift+Tab by default. Wisp's screens are
short, single-column forms, so Up/Down feels more natural and is what most
people try first. ``WispScreen`` adds that everywhere without touching
widgets that already use Up/Down for their own thing (namely an open
``Select`` dropdown, which needs the arrows to move between its options).

All screens should inherit from this instead of ``textual.screen.Screen``.
Textual merges ``BINDINGS`` across the MRO, so a subclass's own bindings
(``escape``, ``1``/``2``/``3``, etc.) keep working unchanged.
"""

from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Select


class WispScreen(Screen):
    """Base screen adding Up/Down as aliases for Shift+Tab/Tab."""

    BINDINGS = [
        Binding("down", "focus_next_widget", "Siguiente", show=False),
        Binding("up", "focus_previous_widget", "Anterior", show=False),
    ]

    def action_focus_next_widget(self) -> None:
        if self._arrows_owned_by_focused_widget():
            return
        self.focus_next()

    def action_focus_previous_widget(self) -> None:
        if self._arrows_owned_by_focused_widget():
            return
        self.focus_previous()

    def _arrows_owned_by_focused_widget(self) -> bool:
        """True when the focused widget needs Up/Down for itself.

        A ``Select`` uses the arrow keys to move between its own options
        (open or not), so we back off and let it handle them instead of
        stealing focus away mid-selection.
        """
        return isinstance(self.focused, Select)
