# Custom VPS demo: configure WireGuard on a server you already own.
#
# This tape performs a REAL deploy against YOUR server: replace the host and
# key path below before recording. The remote installer takes several
# minutes — it is hidden, then the result is shown.
#
# Requirements: vhs, wisp installed, a Linux server reachable over SSH whose
# authorized_keys contains your public key.
#
# Run from the repo root:
#   vhs .github/assets/tapes/demo-vps.tape

Output .github/assets/demo-vps.gif
Set FontSize 16
Set Width 1200
Set Height 720
Set Theme {"background": "#0b0f19", "foreground": "#e2e8f0", "cursor": "#38bdf8"}
Set Padding 40

# Deploy onto your VPS (EDIT the host/key path). The installer runs for
# several minutes on the server — hidden; the connect result is shown.
Type "wisp deploy vps --host 157.137.218.11 --ssh-user ubuntu --wireguard-port 51820 --ssh-key-path ~/.ssh/id_ed25519"
Enter
Sleep 2s
Hide
Sleep 4m
Show
Sleep 2s

# Tunnel proof: with the tunnel up, curl exits through the VPS, so this shows
# the VPS's public IP (safe to publish — the tunnel is destroyed below).
# NEVER run this before deploy or after destroy: it would show the real IP.
Type "curl ifconfig.me"
Enter
Sleep 1s

# Destroy: tears the tunnel down on BOTH ends (server-side wisp-* interface
# included) — real cleanup, keep it visible.
Type "wisp destroy vps --host 157.137.218.11 --ssh-user ubuntu --ssh-key-path ~/.ssh/id_ed25519"
Enter
Sleep 2s
Hide
Sleep 20s
Show
Sleep 1s
