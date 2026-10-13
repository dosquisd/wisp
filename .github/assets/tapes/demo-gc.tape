# Garbage collection demo: find and report leftover Pulumi stacks.
#
# `wisp gc` reads exported state only — fully offline. `--refresh` contacts
# the cloud per stack: stacks without valid credentials fail gracefully and
# are reported line by line (with no AWS account, expect the aws line to say
# so — that is the honest behavior, keep it in the GIF or trim the tape).
#
# NOTE: `wisp gc` shows your REAL stack names/org. If you would rather not
# show them, record this one in a clean environment instead.
#
# Run from the repo root:
#   vhs .github/assets/tapes/demo-gc.tape

Output .github/assets/demo-gc.gif
Set FontSize 16
Set Width 1200
Set Height 720
Set Theme {"background": "#0b0f19", "foreground": "#e2e8f0", "cursor": "#38bdf8"}
Set Padding 40

# Report leftovers.
Type "wisp gc"
Enter
Sleep 7s

# Real deletion
Type "wisp gc --destroy"
Enter
Sleep 20s
