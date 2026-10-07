"""Tunnel view: destroy confirmation (``[general] confirm_destroy``).

The only way out of the tunnel view is destroying the VPN, which is
irreversible, so it must have the described guard: ask by default, skip when
disabled, and persist "no volver a preguntar". ``request_shutdown`` and
``save_session_config`` are stubbed so nothing touches the real daemon or disk.
"""

from textual.widgets import Switch

from wisp.cli.screens.modal import ConfirmDestroyScreen
from wisp.cli.screens.tunnel import TunnelScreen


async def _open_tunnel(pilot, app) -> None:
    app.push_screen(TunnelScreen())
    await pilot.pause()
    await pilot.pause()
    assert type(app.screen) is TunnelScreen


def _stub_shutdown(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "wisp.cli.screens.tunnel.request_shutdown",
        lambda app, reason: calls.append((app, reason)),
    )
    return calls


def _stub_save(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "wisp.cli.screens.tunnel.save_session_config",
        lambda *a, **k: calls.append(a),
    )
    return calls


async def test_destroy_asks_by_default(wisp_app):
    async with wisp_app.run_test(size=(100, 40)) as pilot:
        await _open_tunnel(pilot, wisp_app)

        await pilot.press("d")
        await pilot.pause()

        assert isinstance(wisp_app.screen, ConfirmDestroyScreen)

        await pilot.click("#btn-destroy-no")
        await pilot.pause()
        assert type(wisp_app.screen) is TunnelScreen


async def test_destroy_cancelled_by_escape(wisp_app):
    async with wisp_app.run_test(size=(100, 40)) as pilot:
        await _open_tunnel(pilot, wisp_app)

        await pilot.press("d")
        await pilot.pause()
        assert isinstance(wisp_app.screen, ConfirmDestroyScreen)

        await pilot.press("escape")
        await pilot.pause()
        assert type(wisp_app.screen) is TunnelScreen


async def test_destroy_confirmed_triggers_shutdown(wisp_app, monkeypatch):
    calls = _stub_shutdown(monkeypatch)
    async with wisp_app.run_test(size=(100, 40)) as pilot:
        await _open_tunnel(pilot, wisp_app)

        await pilot.press("d")
        await pilot.pause()
        await pilot.click("#btn-destroy-yes")
        await pilot.pause()

        assert len(calls) == 1
        assert "tunnel destroyed" in calls[0][1]


async def test_destroy_no_ask_persists_and_proceeds(wisp_app, monkeypatch):
    _stub_shutdown(monkeypatch)
    saves = _stub_save(monkeypatch)
    async with wisp_app.run_test(size=(100, 40)) as pilot:
        await _open_tunnel(pilot, wisp_app)
        assert wisp_app.state.config.confirm_destroy is True

        await pilot.press("d")
        await pilot.pause()
        modal = wisp_app.screen
        assert isinstance(modal, ConfirmDestroyScreen)
        modal.query_one("#switch-no-ask-destroy", Switch).value = True
        await pilot.pause()
        await pilot.click("#btn-destroy-yes")
        await pilot.pause()

        assert wisp_app.state.config.confirm_destroy is False
        assert len(saves) == 1


async def test_destroy_skips_modal_when_disabled(wisp_app, monkeypatch):
    calls = _stub_shutdown(monkeypatch)
    async with wisp_app.run_test(size=(100, 40)) as pilot:
        await _open_tunnel(pilot, wisp_app)
        wisp_app.state.config.confirm_destroy = False

        await pilot.press("d")
        await pilot.pause()

        assert len(calls) == 1
        assert not isinstance(wisp_app.screen, ConfirmDestroyScreen)
