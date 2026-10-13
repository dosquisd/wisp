# Demo assets

GIFs and images referenced by the root README live here. Nothing in this
directory is required for Wisp to work — the README renders fine with the
placeholders until the files below exist.

Every GIF is regenerable from a committed VHS tape: edit the tape, run it,
commit the new GIF. No screen-recording guesswork.

## Regenerating the GIFs

```bash
# Install VHS once (needs ttyd + ffmpeg):
brew install vhs          # or: go install github.com/charmbracelet/vhs@latest

# Render any tape (from the repo root):
vhs .github/assets/tapes/demo-tui.tape
```

## The two tiers

**Tier 1 — fully reproducible, no cloud resources touched:**

| Tape | Shows | Notes |
| --- | --- | --- |
| `tapes/demo-config.tape` | Config screen edits + Save modal | Offline: `XDG_CONFIG_HOME=/tmp/wisp-demo` isolates the config |
| `tapes/demo-gc.tape` | `wisp gc` + `--refresh` | Reads real stack names — record in a clean environment if you prefer. `--destroy` is commented out (real deletion) |

**Tier 2 — perform a REAL deploy (costs nothing on OCI free tier / GCP SPOT, but the VM exists for a couple of minutes):**

| Tape | Shows | Notes |
| --- | --- | --- |
| `tapes/demo-tui.tape` | Hero: full TUI flow | **No AWS needed**: deploys to OCI (swap to `gcp` in the tape if preferred). Boot wait is hidden with `Hide`/`Sleep`/`Show` |
| `tapes/demo-cli.tape` | `wisp deploy` + `wisp destroy` on OCI | Same Hide/Show trick |
| `tapes/demo-vps.tape` | Real deploy against YOUR server | Edit host/key path before running |

With no AWS account, the deploy wizard shows "(Using standard AWS region
list)" when AWS is selected — that is the region-fallback fix working as
designed, but the demos deliberately use OCI/GCP instead.

## Shot list

| File | Clip | Duration | The story it tells |
| --- | --- | --- | --- |
| `demo-tui.gif` | Full TUI flow: main menu -> deploy wizard -> progress -> tunnel view with uptime -> destroy confirm -> menu | 30-45s | The hero. This is the first thing anyone sees — the whole product in one loop. No `curl` step: the tunnel proof is the uptime ticker (running curl inside/outside the TUI is not possible / would leak the real IP). |
| `demo-cli.gif` | `wisp deploy oci -r sa-bogota-1` -> result JSON -> `curl ifconfig.me` (shows the VM's IP — tunnel proof) -> `wisp destroy` | 15-20s | Scriptable, clean exit, and the tunnel provably routes. The curl step is only safe while the tunnel is up: before deploy / after destroy it would show the real IP. |
| `demo-vps.gif` | `wisp deploy vps --host ... --ssh-user root` -> result -> `curl ifconfig.me` (tunnel proof) -> `wisp destroy vps` | 15-20s | No cloud account needed — the differentiator. Same curl caveat. |
| `demo-gc.gif` | `wisp gc` -> `wisp gc --refresh` | 10-15s | Crashed sessions don't burn money: Wisp finds and reports orphans. |
| `demo-config.gif` | Config screen: edit TTL and port -> Save modal | 10s | The settings story; shows the TTL watchdog field. |
| `logo.png` | Static | — | Simple mark: a flame/wisp over a wireframe globe reads well small. |

Recording order tip: record `demo-tui.gif` LAST, after a couple of dry runs —
the flow looks smoothest when the keystrokes are muscle memory.

## Recording spec

- **Tool:** VHS from the committed tapes (see above). GUI alternatives for
  ad-hoc shots: ScreenToGif (Windows), Kap (macOS), Peek (Linux).
- **Size:** 1200x720. Record at final resolution; never rescale.
- **Font:** 14-16pt monospace — it must be readable on a phone.
- **Frame rate:** 24fps.
- **Length:** hero under 45s; everything else under 20s.
- **File size:** keep every GIF under ~10MB or GitHub renders it badly.
  Compress with `gifsicle -O3 --lossy=80 -o out.gif in.gif` or
  `ffmpeg -i in.gif -vf "fps=24,scale=1200:-1:flags=lanczos" out.gif`.
- **Theme:** the tapes already set Wisp's dark background (`#0b0f19`) so the
  GIFs blend with the README.
- **Trim dead time:** cut pauses longer than ~1s; the GIF should feel brisk.

### Tweaking a tape

VHS drives the TUI with real keystrokes, so the `Sleep` values are
best-effort: on the first render, if a screen has not settled before the next
key lands, bump that `Sleep`. Focus-order comments in each tape mark the
spots that most often need adjusting (which button is focused first in a
modal, how many `Tab`s reach a button).
