---
name: hermes-desktop-app
description: Configure and use the Hermes Desktop app (native Windows/macOS/Linux GUI) and integrate Hermes into everyday OS use — Quick Entry global-hotkey popup (the "Copilot-like" composer), remote-backend wiring so a Windows GUI drives a WSL/headless agent, wake word, and the messaging gateway. Load when the user asks for a chat UI that pops up on demand, a desktop app, global hotkey, overlay, or "make Hermes work like Copilot" on Windows.
---

# Hermes Desktop App & Windows Integration

Hermes ships multiple front-ends that ALL share one agent state (config, keys, sessions, skills, memory): CLI (`hermes`), TUI (`hermes --tui`), **Desktop app** (`hermes desktop`), Web Dashboard (`hermes dashboard`), and the Messaging Gateway (Telegram/WhatsApp/Discord/Signal, 20+ platforms). Sessions start in one and resume in another.

## Quick Entry — the Copilot-style popup (the feature users usually mean)

- A small always-available composer summoned by a **global hotkey from anywhere on the system** — fire a prompt without opening the main window.
- Enable: **Settings → Advanced → Quick Entry**. Default shortcut **Ctrl/Cmd+Shift+Space**; user-settable (needs ≥1 modifier). If another app owns the chord, the settings row flags the conflict.

## Fast facts (verified against docs, Aug 2026)

- **Launch**: `hermes desktop` (installs workspace Node deps, builds unpacked Electron app, launches). Installer on hermes-agent.nousresearch.com installs CLI + Desktop together; `hermes desktop` also works after a CLI-only install.
- **Desktop features**: streaming chat w/ live tool activity, drag-drop files, right preview rail, Ctrl+F find-in-chat, embedded terminal (Ctrl+`), git review pane + worktrees (Ctrl+G / Ctrl+Shift+B), artifacts gallery, Memory Graph (`/journey`), multi-window (Ctrl+Shift+N), command palette (Ctrl+K/P), rebindable shortcuts, VS Code Marketplace theme import, keep-awake toggle.
- **Voice + wake word**: same voice pipeline as CLI/TUI; wake word ("Hey Hermes", fully on-device) via `/wake on|off|status` or the composer ear icon; config `wake_word.enabled` in `~/.hermes/config.yaml`. Engines: openWakeWord (free, bundled "hey hermes"), sherpa (any phrase), Porcupine (needs key). Works on CLI, TUI, and desktop.
- **Docs lookup**: the docs site's full text is served as `https://hermes-agent.nousresearch.com/docs/assets/files/llms-full-<hash>.txt` — link it from the docs index HTML and `curl` it to grep the whole doc set. `web_extract` FAILS on docs pages when `web.extract_backend` is the DDG search-only backend — use curl, not web_extract, for docs research.

## Wiring a Windows Desktop GUI to a WSL/remote agent (reuse existing skills/memory)

A native Windows Hermes install gets its OWN `~/.hermes` — separate skills, memory, sessions. To keep ONE agent (the WSL one with all its skills), point the Desktop app at the WSL agent via **Remote Gateway**:

1. Backend side (WSL): add creds to `~/.hermes/.env` (chmod 600):
   `HERMES_DASHBOARD_BASIC_AUTH_USERNAME`, `HERMES_DASHBOARD_BASIC_AUTH_PASSWORD`, `HERMES_DASHBOARD_BASIC_AUTH_SECRET` (stable signing secret via `openssl rand -base64 32` so sessions survive restarts).
2. Run `hermes serve --host <wsl-ip> --port 9119` (non-loopback bind auto-engages the auth gate). Keep it alive — systemd/tmux. The app does NOT start the backend for you.
3. App side (Windows): **Settings → Gateway → Remote gateway** → `http://<wsl-ip>:9119`, sign in.
- Public-internet reach → use OAuth (Nous Portal) instead of basic auth; LAN/VPN (Tailscale) is fine for basic auth.
- Voice/wake word work against a remote backend: desktop captures the local mic and streams PCM to the backend (client capture, automatic).
- Messaging alternative: `hermes gateway` on the agent host → chat from Telegram/WhatsApp/Discord anywhere, no UI work at all.

## Pitfalls

- **Separate state**: a Windows-native install does NOT share the WSL agent's skills/memory. Remote Gateway is the bridge; don't promise shared state otherwise.
- **Desktop inside WSL (WSLg) is janky** — for a real Windows UI, install the app natively on Windows and point it at the WSL `hermes serve` backend.
- **`hermes update` on Windows refuses while another `hermes.exe` holds the venv entry point** (Desktop's spawned backend, an open REPL, or a running gateway). Close Desktop/REPLs, stop the gateway, then update; `--force-venv` only bypasses the venv-interpreter guard, not the process guard.
- One dashboard backend on :9119 serves ALL co-located profiles via the profile switcher — no second port per profile.
- Don't hardcode the docs hash — grep the index page (`/docs`) for `llms-full` first; it changes per build.

## Reference

- `references/desktop-app-details.md` — condensed doc detail: full feature list, shortcuts, wake-word config surface, remote-backend auth modes, env vars.
- Adjacent: `hermes-voice-mode` (voice pipeline), `hermes-tui-configuration` (terminal UI), `hermes-reliability-tuning` (API config).

## Verification

- Quick Entry: enable in Settings → Advanced, press the hotkey from any app, confirm composer appears.
- Remote wiring: `curl http://<wsl-ip>:9119` from Windows returns the auth-gated dashboard; app connects and resumes a WSL session.
