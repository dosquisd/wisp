# CLI demo: deploy -> destroy on OCI (free tier — swap to `gcp` if preferred).
#
# Requirements: vhs, wisp installed, OCI credentials in ~/.oci/config.
# This tape performs a REAL deploy and destroy.
#
# Run from the repo root:
#   vhs .github/assets/tapes/demo-cli.tape

Output .github/assets/demo-cli.gif
Set FontSize 16
Set Width 1200
Set Height 720
Set Theme {"background": "#0b0f19", "foreground": "#e2e8f0", "cursor": "#38bdf8"}
Set Padding 40

# Deploy: provisioning + boot wait are real. Keep them hidden; show
# the JSON result and the brief tqdm moment after the wait finishes.
Type "wisp deploy oci -r sa-bogota-1"
Enter
Sleep 5s
Hide
Sleep 120s
Show
Sleep 4s

# Tunnel proof: with the tunnel up, curl exits through the VM, so this shows
# the VM's public IP (safe to publish — the VM is destroyed moments later).
# NEVER run this before deploy or after destroy: it would show the real IP.
Type "curl ifconfig.me"
Enter
Sleep 3s

# Destroy everything back (stack.cancel + destroy + local cleanup).
Type "wisp destroy oci -r sa-bogota-1"
Enter
Hide
Sleep 80s
Show
Sleep 2s
