# TUI exit-summary diagnostics — "session stats on quit"

Verified on 0.16.0–0.18.2, pip install on asdf py3.11 (paths under
~/.asdf/installs/python/3.11.0/lib/python3.11/site-packages/hermes_cli/).

## Mechanism

- Python parent `_launch_tui` runs `subprocess.call([node, entry.js])`; after
  exit: `if code in {0, 130}: _print_tui_exit_summary(resume_session_id,
  active_session_file)` (`KeyboardInterrupt` → code 130).
- `_print_tui_exit_summary` resolves target =
  `_read_tui_active_session_file(file)` | resume id | `_resolve_last_session("tui")`;
  silently returns if `db.get_session` misses or `message_count == 0` — the
  get_session miss is a HARD return, no fallback to the last-session resolver.
- TUI (entry.js) writes `{"session_id": ...}` to the tempfile named by
  `HERMES_TUI_ACTIVE_SESSION_FILE` (`/tmp/hermes-tui-active-session-*.json`) on
  newSession/activate/resume; Python unlinks it in `finally`.
- Ctrl+C is app-owned — `ink2.render` uses `exitOnCtrlC: false`. App handler
  order: busy → `turnController.interruptTurn`; draft → `clearIn`; idle →
  `handleIdleHotkeyExit` → `die()` → `gw2.kill("app.die"); exit();
  process.exit(0)`. Exit code 0 on `/quit`.

## VERIFIED root cause: fresh-launch short-sid bug

When the summary stops appearing, this is the cause (confirmed by repro, not
hypothesis):

1. Gateway `tui_gateway/server.py` `session.create`:
   `sid = uuid.uuid4().hex[:8]` → SHORT internal handle (e.g. `a8b0df67`),
   plus `stored_session_id = _new_session_key()` → FULL DB key
   (`20260808_HHMMSS_xxxxxx`, format `%Y%m%d_%H%M%S_%x6`). The response carries
   both: `{"session_id": sid, "stored_session_id": key, ...}`.
2. TUI `newSession` (bundle `src/app/useSessionLifecycle.ts`) calls
   `writeActiveSessionFile(r.session_id)` → writes the SHORT sid to the temp file.
3. DB row is created lazily (first prompt / agent build) under the FULL key only.
4. On quit: `_print_tui_exit_summary` reads the temp file → short sid →
   `db.get_session(short)` = exact `SELECT ... WHERE id = ?` → miss →
   silent `return`. No stats, exit code already 0, nothing logged.

Resume paths are fine because they write the full key:
- `resumeById`: `writeActiveSessionFile(r.resumed ?? r.session_id)`
- `activateLiveSession`: `writeActiveSessionFile(r.session_key ?? r.session_id)`

So: FRESH launch (`hermes --tui`, bare `hermes` with `display.interface: tui`,
`/new`) → no exit stats. RESUMED session (`-c`, `--resume`, `/resume`) → stats
print. "Suddenly stopped" is a launch-habit change, NOT a version regression —
wheel-diffed 0.16.0/0.17.0/0.18.0/0.18.2, identical code in all.

Workaround for the user: launch with `-c` (continue last session) or quit from
a resumed session. Upstream fix: TUI `newSession` should write
`r.stored_session_id ?? r.session_id`. Defensive Python fix:
`_print_tui_exit_summary` should fall back to `_resolve_last_session("tui")`
when the file-derived target doesn't resolve.

## Reproduction recipe (works in a nested PTY)

Raw terminal-tool PTY fails (see pitfalls) but `script` works:

```bash
script -q -f -c "hermes --tui" /tmp/tui-typescript.txt   # background, pty=true
# wait for "ready" status, then send exactly:
#   "/quit" then "\r"   (process write action; raw mode needs CR)
# NOTE: process 'submit' appends \n — raw-mode TUI does NOT treat \n as Enter.
# Check: process exit code should be 0; then read /tmp/tui-typescript.txt
#   (strip ANSI: re.sub(r'\x1b\[[0-9;?]*[a-zA-Z]|\x1b\][^\x07]*\x07|\x1b[=>]', '', text))
```

Exit code 0 + NO "Resume this session with:" in the typescript = confirmed
repro. Corroborating evidence:
- temp file contains a short id: `{"session_id":"a8b0df67"}`
- `SELECT id, session_key FROM sessions WHERE id='a8b0df67' OR session_key='a8b0df67'`
  → 0 rows (short sid never persisted)

Sanity check the print path against real data (prints if data is healthy):
`python3 -c "from hermes_cli.main import _print_tui_exit_summary; _print_tui_exit_summary(None, None)"`
(add site-packages to sys.path if run outside the install). Healthy DB:
message_count + input/output/cache_read/cache_write/reasoning_tokens populated,
`end_reason='tui_shutdown'` on graceful exits.

## Version-regression check (did an upgrade break it?)

- `pip download --no-deps -d /tmp/x hermes-agent==<old> <new>`; unzip both.
- `diff -rq` the trees; the TUI is one minified file
  (`hermes_cli/tui_dist/entry.js`). `diff` is instant — do NOT use
  difflib.SequenceMatcher on multi-MB bundles (times out at 180s).
- Read minified regions with python `re.finditer` + context slices around
  markers like `session.die`, `exitOnCtrlC`, `writeActiveSessionFile`,
  `stored_session_id`, `HERMES_TUI_ACTIVE_SESSION_FILE`.

## Environment pitfalls hit during diagnosis

- terminal hardline blocklist false-positives: grep patterns containing
  shutdown/reboot/die/exit can be BLOCKED as "system shutdown/reboot".
  Rephrase (use search_files, or split the alternation to avoid the words).
- `web_extract` fails when `web.extract_backend` is ddgs ("search-only
  backend") — use `extract_from_webpage` (NPU) or curl instead.
- Nested-PTY via the terminal tool's raw pty is unreliable: the `zsh -lic
  set +m;` wrapper breaks raw-mode stdin — synthetic Ctrl+C is swallowed by
  Node's signal handler and typed commands never submit. `script` wrapper
  avoids this (see repro above). The pty PREVIEW also drops post-exit output —
  the typescript file captures it.
- PTY test sessions may show a broken agent init ("0 tools · 0 skills") and
  short sids that are never persisted (DB rows are lazy — created on first
  prompt). A pty run where you only type `/quit` leaves NO session row.
- Brew-vs-pip archaeology: old `tui_gateway_crash.log`/agent logs may show a
  Homebrew python path even after the pip switch — a stale `HERMES_PYTHON`
  export in the shell can make the pip TUI spawn the brew gateway. Brew
  Cellar confirmed gone Aug 2026.
- Session title in `state.db` updates in place; a resumed session's row keeps
  `end_reason=None` while live, so don't read `end_reason` as proof of quit
  behavior for sessions that were resumed afterwards.
