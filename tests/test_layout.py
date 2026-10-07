"""Layout regressions: nothing the user must see may scroll out of reach.

Textual's default cards use `max-height: 100%` with `overflow-y: auto`, so any
card taller than the terminal grows a scrollbar. The deploy screen is the one
whose bottom (the Start/Cancel buttons) must stay reachable; on a 24-row
terminal a scrollbar elsewhere is tolerable, but the progress and menu cards
must fit the smallest realistic terminal.
"""


async def test_deploy_card_fits_a_24_row_terminal(wisp_app):
    """The deploy card must not overflow, so the buttons are never clipped."""
    async with wisp_app.run_test(size=(100, 24)) as pilot:
        await pilot.pause()
        wisp_app.push_screen("deploy")
        await pilot.pause()

        card = wisp_app.screen.query_one(".card")
        assert card.virtual_size.height <= card.container_size.height, (
            "deploy card overflows: "
            f"virtual={card.virtual_size.height} container={card.container_size.height}"
        )


async def test_progress_card_fits_even_with_error(wisp_app):
    """The progress card must not scroll, including after a failed deploy."""
    async with wisp_app.run_test(size=(100, 24)) as pilot:
        await pilot.pause()
        from wisp.cli.screens.progress import ProgressScreen

        screen = ProgressScreen()
        wisp_app.push_screen(screen)
        await pilot.pause()
        ProgressScreen.run_deployment_worker = lambda self: None  # type: ignore[method-assign]
        screen._handle_error("Falló el despliegue: credenciales inválidas en us-east-1")
        await pilot.pause()

        card = screen.query_one(".card")
        assert card.virtual_size.height <= card.container_size.height, (
            f"progress card overflows: virtual={card.virtual_size.height}"
        )


async def test_progress_bar_is_centered(wisp_app):
    """The ProgressBar must sit in the middle of the card content, not hug the left."""
    async with wisp_app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        from wisp.cli.screens.progress import ProgressScreen

        screen = ProgressScreen()
        wisp_app.push_screen(screen)
        await pilot.pause()

        card = screen.query_one(".card")
        bar = screen.query_one("#progress-bar")
        card_left = card.content_region.x
        card_width = card.content_region.width
        bar_center = bar.region.x + bar.region.width / 2
        expected = card_left + card_width / 2
        assert abs(bar_center - expected) <= 1, (
            f"progress bar off-centre by {bar_center - expected:+.1f} cols"
        )
