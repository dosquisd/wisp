"""Focus-order regressions.

Textual keeps walking the focus chain through widgets that are not actually on
screen, so anything hidden with `display: none` must also be removed from the
focus order or it becomes a place the keyboard can get stuck.
"""

from conftest import SCREENS
from textual.widgets import Button


async def test_main_menu_never_autofocuses_a_hidden_widget(wisp_app):
    """The first focused widget must be visible.

    Regression: the orphan-cleanup button was composed before the three main
    buttons, so it won autofocus while `display: none` and trapped the user.
    """
    async with wisp_app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        focused = wisp_app.focused
        assert focused is not None
        assert focused.display, f"autofocus landed on hidden widget {focused.id!r}"
        assert focused.id == "btn-deploy"


async def test_main_menu_arrows_walk_the_three_options(wisp_app):
    """Down/Up must cycle deploy -> config -> quit and stop there."""
    async with wisp_app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()

        walked = [wisp_app.focused.id]
        for _ in range(2):
            await pilot.press("down")
            walked.append(wisp_app.focused.id)

        assert walked == ["btn-deploy", "btn-config", "btn-quit"]

        # And back up again, never landing on the hidden orphan button.
        await pilot.press("up")
        await pilot.press("up")
        assert wisp_app.focused.id == "btn-deploy"


async def test_hidden_orphan_button_is_not_focusable(wisp_app):
    """`btn-orphan-cleanup` is hidden by default and must stay unfocusable."""
    async with wisp_app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        button = wisp_app.screen.query_one("#btn-orphan-cleanup", Button)
        assert button.display is False
        assert button.can_focus is False


async def test_left_right_walk_a_horizontal_button_group(wisp_app):
    """Left/Right move within a button row, as Tab already does."""
    async with wisp_app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        wisp_app.push_screen("deploy")
        await pilot.pause()

        deploy = wisp_app.screen.query_one("#btn-start-deploy", Button)
        deploy.focus()
        await pilot.pause()

        await pilot.press("right")
        assert wisp_app.focused.id == "btn-cancel"

        await pilot.press("left")
        assert wisp_app.focused.id == "btn-start-deploy"


async def test_input_keeps_its_own_left_and_right(wisp_app):
    """Typing in an Input must move the cursor, not the focus.

    `Input` binds left/right itself, and Textual resolves bindings from the
    focused widget upwards, so the screen-level bindings must not shadow it.
    """
    async with wisp_app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        wisp_app.push_screen("config")
        await pilot.pause()

        field = wisp_app.screen.query_one("#input-vm-boot-timeout")
        field.focus()
        field.value = "6000"
        field.cursor_position = 3
        await pilot.pause()

        await pilot.press("left")
        assert field.cursor_position == 2
        assert wisp_app.focused is field


async def test_every_screen_yields_at_least_one_focusable_widget(wisp_app):
    """No installed screen may have an empty focus chain."""
    async with wisp_app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        for name in SCREENS:
            wisp_app.push_screen(name)
            await pilot.pause()
            await pilot.pause()
            focusable = [w.id for w in wisp_app.screen.focus_chain]
            assert focusable, f"{name} has no focusable widget"
            wisp_app.pop_screen()
            await pilot.pause()
