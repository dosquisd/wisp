# Hero demo: full TUI flow on OCI (free tier — swap to `gcp` below if preferred).
#
# Requirements:
#   - vhs installed (https://github.com/charmbracelet/vhs): brew install vhs
#     or go install github.com/charmbracelet/vhs@latest (needs ttyd + ffmpeg)
#   - wisp installed: uv tool install --editable .
#   - OCI credentials in ~/.oci/config (this tape performs a REAL deploy and
#     a real destroy; the VM lives for ~1 minute on the free tier)
#
# Run from the repo root:
#   vhs .github/assets/tapes/demo-tui.tape
#
# NOTE: keystroke timings below are best-effort. On the first render, adjust
# the Sleeps so each screen settles before the next key lands.

Output .github/assets/demo-tui.gif
Set FontSize 16
Set Width 1200
Set Height 720
Set Theme {"background": "#0b0f19", "foreground": "#e2e8f0", "cursor": "#38bdf8"}
Set Padding 40

# Launch the TUI and let the main menu settle.
Type "wisp"
Enter
Sleep 3s

# Main menu -> Deploy (binding "1").
Type "1"
Sleep 1s

# Deploy wizard: provider Select is focused. Open it, pick OCI, confirm.
Enter
Sleep 500ms
Down
Down
Sleep 500ms
Enter
Sleep 1s

# Region Select
Tab
Sleep 250ms
Tab
Sleep 250ms
Tab
Sleep 250ms

# Move focus to "Start Deployment" and launch the real deploy.
Tab
Sleep 1s
Enter

# The progress screen streams the installer output. The boot wait is real
# hide the recording so the GIF stays short, then show the result.
Sleep 2s
Hide
Sleep 104s
Show

# Deploy success -> the tunnel view replaces the screens automatically.
# Let the uptime ticker run for a few seconds so it is visibly alive.
Sleep 10s

# Destroy: `d` opens the confirmation modal. Navigate to "Yes, Destroy"
# (arrows cycle focus between the switch and the buttons) and confirm.
Type "d"
Sleep 1s
Down
Sleep 250ms
Down
Sleep 500ms
Enter

# Shutdown screen runs the real teardown (stack.cancel + destroy), then
# returns to the main menu. Let the cleanup finish before quitting.
Sleep 5s
Hide
Sleep 55s
Show
Sleep 6s

# Back on the menu — quit cleanly.
Type "q"
Sleep 1s
