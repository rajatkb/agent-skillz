# ~/.hermes Directory Audit — Junk vs Keep

Reusable taxonomy from an Aug 2026 audit of `~/.hermes` on this machine. Use this as the
starting checklist when the user asks to clean up the Hermes home dir. Always `du -sh` +
`ls -lt` before deleting, and confirm with the user — they approve deletions explicitly.

## Junk (safe to delete when present)

| Item | Why junk |
|---|---|
| `config.yaml.bak.*` | Auto-config backups from `hermes config` edits. User explicitly hates `.bak` clutter. Config never references them. |
| `sessions/request_dump_*.json` | One-off debug request dumps (crash artifacts). Old ones (weeks+) are dead weight. |
| `interrupt_debug.log` | Stale debug log. |
| `auth.lock`, `shell-hooks-allowlist.json.lock` | Zero-byte stale lock files. |
| `cache/delegation/subagent-summary-*.txt` | Old subagent summaries. |
| `cache/screenshots/browser_*.png` | One-off browser screenshots. |
| `logs/tui_gateway_crash.log`, `logs/gui.log`, `logs/update.log` | Old crash/UI logs. |
| `pastes/paste_*.txt` | Clipboard paste history — user cares about session privacy, so old pastes are cleanup candidates. |
| `images/clip_*.png` | Old clipboard captures. |

## Keep (functional — do NOT delete)

| Item | Why keep |
|---|---|
| `state.db` (+`-shm`/`-wal`) | **The session database** — core to Hermes, used by session_search. Can be 150+ MB. |
| `skills/`, `scripts/`, `plugins/`, `cron/`, `memories/`, `platforms/` | Active config. |
| `config.yaml`, `.env`, `auth.json`, `SOUL.md` | Config. |
| `logs/agent.log`, `logs/errors.log` | Active logs, being written right now. |
| `lsp/` (can be 100+ MB of node_modules) | bash-language-server — **used by Hermes' file tools**, not dead weight despite the size. |
| `cache/model_catalog.json`, `cache/openrouter_model_metadata.json`, `models_dev_cache.json` | Live model caches, regenerated on demand anyway. |
| `bin/` (uv, uvx, tirith), `agent-hooks/`, `crawl_sessions/` | Active tooling. |
| `verification_evidence.db`, `processes.json`, `.hermes_history`, `.update_check` | Functional state. |

## Empty dirs

`hooks/`, `pairing/`, `image_cache/`, `audio_cache/` — often empty; Hermes recreates them
as needed. No point deleting, harmless to leave.

## Process notes

- Deleting 10+ files in one `rm` triggers Hermes' mass-deletion security scan (user must approve).
- Check `processes.json` before cleaning `crawl_sessions/` — a research loop may be writing there.
- Session state is only persisted at round boundaries, so a killed `research.py` may leave
  half-written session folders that LOOK finished but have no `05_synthesis/`. Re-run to resume.
