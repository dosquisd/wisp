# Config screen demo: edit settings, save through the confirmation modal.
#
# Fully offline: XDG_CONFIG_HOME points the TUI at a throwaway config dir, so
# the real wisp.toml is never touched. Delete /tmp/wisp-demo afterwards.
#
# Requirements: vhs, wisp installed.
#
# Run from the repo root:
#   vhs .github/assets/tapes/demo-config.tape

Output .github/assets/demo-config.gif
Set FontSize 16
Set Width 1200
Set Height 720
Set Theme {"background": "#0b0f19", "foreground": "#e2e8f0", "cursor": "#38bdf8"}
Set Padding 40

# Launch the TUI against an isolated config dir.
Type "XDG_CONFIG_HOME=/tmp/wisp-demo wisp"
Enter
Sleep 3s

# Main menu -> Settings (binding "2").
Type "2"
Sleep 1s

# The VM Boot Timeout input is focused first: clear it and type a new value.
# Backspace count matches the current value's length ("60" -> 2).
Backspace
Backspace
Type "30"
Sleep 1s

# Walk to the Session TTL input (5 fields down: port, interface, dns1, dns2,
# ttl) and set it too.
Tab
Tab
Tab
Tab
Tab
Sleep 500ms
Backspace
Backspace
Type "120"
Sleep 1s

# Walk to the Save button and press it. Focus order: switch -> Save -> Reset
# -> Back; adjust the Tab count if focus lands elsewhere.
Tab
Tab
Tab
Tab
Tab
Sleep 500ms
Enter
Sleep 1s

# The "Save settings?" modal is open; confirm (navigate to Save if the
# Cancel button has focus first).
Down
Sleep 500ms
Enter
Sleep 2s

# Settings saved notification, then leave back to the menu.
Sleep 1s
Type "q"
Sleep 2s
