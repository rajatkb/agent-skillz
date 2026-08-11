# Hermes Desktop App — condensed doc detail (verified Aug 2026)

Source: hermes-agent.nousresearch.com/docs full-text dump (`llms-full-*.txt`).

## Surfaces (all share one agent state)

- Desktop App (`hermes desktop`, alias `gui`) — native Electron app, macOS/Windows/Linux.
- CLI / TUI (`hermes --tui`) — terminal.
- Web Dashboard (`hermes dashboard`, port 9119 when `HERMES_DASHBOARD=1`) — browser admin; Chat tab embeds the TUI.
- Gateway — messaging platforms (Telegram, Discord, Slack, WhatsApp, Signal, Matrix, Mattermost, Email, SMS, Teams, Google Chat, + more, 20+).

Sessions are interchangeable across surfaces.

## Desktop feature checklist

- Streaming responses, live tool activity, structured tool-call summaries.
- Drag-drop files into chat; right preview rail; Ctrl+F find-in-chat.
- Composer history (up/down in empty composer); queue editing; Stop/Esc pauses queue.
- Conversation timeline rail on long chats.
- Status bar: per-session YOLO toggle, context-usage meter w/ token breakdown, right-click customizable.
- Repo discovery for Projects sidebar: `desktop.repo_scan_enabled`, `repo_scan_roots`, `repo_scan_exclude_paths` in config.yaml.
- Model picker in composer (sticky per-device, never touches profile default).
- File browser; Artifacts gallery (images/files/links per session).
- Tabs Ctrl+T, windows Ctrl+Shift+N, panes Ctrl+B / Ctrl+J.
- Terminal in right sidebar: Ctrl+` show, Ctrl+Shift+` new, shells persist while hidden, "Add to chat" from selection.
- Git review Ctrl+G (stage/revert/commit/PR via gh), worktrees Ctrl+Shift+B.
- Memory Graph: `/journey` (aliases `/learning`, `/memory-graph`).
- **Quick Entry**: Settings → Advanced → Quick Entry; default Ctrl/Cmd+Shift+Space; requires ≥1 modifier.
- Wake word: ear icon in composer; `/wake on|off|status`.
- Settings UI for providers/keys, models, toolsets, MCP, gateway, sessions; onboarding; VS Code Marketplace theme import; keep-computer-awake.
- Keyboard: Ctrl+K/P palette, Ctrl+/ shortcuts panel, Ctrl+N new session, Ctrl+. Command Center, Ctrl+, Settings, Ctrl+Shift+F search sessions, Ctrl+1–9 profiles, Shift+X light/dark.
- Uninstall: Settings → About → Danger zone (`hermes uninstall --gui` / `--full`).

## Wake word

- `wake_word.enabled` (default off), `surface: auto|cli|tui|gui`, `input_device`, `capture: auto|local|client`, `provider: openwakeword|sherpa|porcupine`, `phrase` (label), `sensitivity` (0.6 default; higher = stricter), `confirmation_frames` (3 default, openWakeWord only), `start_new_session`.
- Engines: openWakeWord free/local ONNX, bundled "hey hermes" model, also hey_jarvis/alexa/hey_mycroft; sherpa = any phrase (~13 MB model); Porcupine = Picovoice, needs `PORCUPINE_ACCESS_KEY`.
- openWakeWord backend: tflite on Apple Silicon, onnx elsewhere (onnx scores near-zero on macOS ARM64 — known issue).
- Client capture: remote backend w/o mic → desktop streams local mic PCM via `wake.feed` RPC; detection still runs on backend.
- Install ahead: `cd ~/.hermes/hermes-agent && uv pip install -e ".[wake]"` (desktop installs w/ `--include-desktop` pre-install).
- Desktop voice: say "stop"/"never mind"/"goodbye"/"cancel" to end a voice conversation.

## Remote backend (Desktop → `hermes serve`)

- App setting: Settings → Gateway → Connection mode → Remote gateway (URL + sign-in) or Hermes Cloud. Per-profile.
- Backend = a running `hermes serve` process (NOT the gateway — separate process for messaging channels).
- Auth: basic username/password for LAN/trusted (creds in `~/.hermes/.env`, 0600); OAuth (Nous Portal) for public internet; `hermes dashboard register` provisions OAuth client.
- Env: `HERMES_DASHBOARD_BASIC_AUTH_USERNAME`, `_PASSWORD` (or `_PASSWORD_HASH` scrypt), `_SECRET` (stable signing; random per boot otherwise → logout on restart).
- Run: `hermes serve --host 0.0.0.0 --port 9119`; non-loopback bind engages auth gate. Keep alive via systemd/tmux.
- Tailscale: bind to tailnet IP, use `http://<tailscale-ip>:9119`.

## Desktop env vars / CLI flags

- `hermes desktop --cwd <path>` / `HERMES_DESKTOP_CWD` — initial project dir.
- `HERMES_DESKTOP_HERMES_ROOT` — source-checkout override (`--hermes-root`).
- `HERMES_DESKTOP_IGNORE_EXISTING=1` — ignore `hermes` on PATH during backend resolution.
- `terminal.font_family` config — embedded terminal font (e.g. `MesloLGS NF`); Settings → Appearance → Terminal Font.

## Update lock (Windows)

`hermes update` refuses if another `hermes.exe` holds the venv entry point (Desktop backend, open REPL, running gateway). Guard on the venv interpreter is NOT bypassed by `--force`; use explicit `hermes update --force-venv` only when holders are false positives.
