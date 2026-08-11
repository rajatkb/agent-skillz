---
name: hermes-tui-configuration
description: "Configure the Hermes TUI surface — reveal/collapse tool, thinking, and subagent output (the '/details' accordion), display keys, skins, busy indicator, theme. Covers the classic-CLI /verbose analog."
tags: [hermes, tui, display, config, details, verbose, accordion]
category: devops
---

# Hermes TUI Configuration — Show/Hide Tool Output & Display Tweaks

## Trigger

- User wants to SEE the progress / terminal output of underlying tool calls or delegated tasks in the TUI instead of collapsed chevrons
- User wants to hide noise (collapse thinking/tools/activity back under chevrons)
- Any question about skins, busy indicator, mouse tracking, light/dark theme, or TUI display config keys
- Questions about quitting the TUI: session stats on exit ("Resume this session with:" epilogue), Ctrl+C behavior, why the exit summary stopped appearing

## The core lever: `/details` (runtime) + `display.details_mode` (persistent)

The TUI renders each turn as collapsible accordion sections: `thinking`, `tools`, `subagents`, `activity`.

- **Runtime, whole session:** `/details expanded` (or `hidden` | `collapsed` | `cycle`)
- **Runtime, one section:** `/details tools expanded`, `/details subagents expanded`, etc.
- **Persistent** (config.yaml, under the existing `display:` block):
```yaml
display:
  details_mode: expanded        # hidden | collapsed | expanded — global accordion default
  sections:
    thinking: expanded          # stream reasoning inline
    tools: expanded             # tool calls + results open
    subagents: expanded         # delegated tasks open instead of chevron
    activity: collapsed         # opt the activity panel IN (hidden by default)
```

**Defaults:** thinking=expanded, tools=expanded, subagents=falls through to global details_mode (collapsed), activity=hidden. Per-section overrides beat both the section default and the global mode. Explicit `display.sections` entries keep existing configs working unchanged.

**Caveat:** expanded shows a live status row while a tool runs, but full terminal output renders when the call COMPLETES — there is no live tail of a running command in the TUI. For long background tasks: status line shows `▶ N`, and `display.sections.activity: collapsed` opts the activity panel back in for background notifications.

## Classic CLI analog

`/verbose` cycles tool-output display modes: off → new → all → verbose. `display.tool_preview_length` caps preview characters shown. `display.tool_progress: verbose` is the classic-CLI key (this machine already sets it).

## Other verified TUI keys

- `display.tui_status_indicator: kaomoji | emoji | unicode | ascii` — busy spinner style (runtime: `/indicator`)
- `display.mouse_tracking: off | wheel | buttons | all` — `wheel` recommended inside tmux (silences prompt-row "No image in clipboard" hover spam)
- `HERMES_TUI_THEME=light | dark | <6-hex>` — force theme (overrides auto-detection)
- `HERMES_TUI_RESUME=1` — auto-resume most recent TUI session on launch
- `display.interface: tui` — make bare `hermes` / `hermes chat` launch the TUI (explicit `--cli`/`--tui` flags always win)
- `/details <section> <mode>` — per-section runtime override; sections: thinking, tools, subagents, activity

## Session stats on quit (exit summary)

Quitting the TUI prints a shell-visible epilogue AFTER the TUI exits:
`Resume this session with:` + Session ID / Title / Messages / token breakdown
(in/out/cache/reasoning). It is NOT rendered by the TUI — the Python parent
prints it in `hermes_cli/main.py::_print_tui_exit_summary`, gated on the Node
subprocess exiting with code 0 or 130. Data comes from the `sessions` table in
`~/.hermes/state.db`.

Ctrl+C is app-owned (Ink runs with `exitOnCtrlC: false`):
- busy turn → first Ctrl+C only interrupts
- draft in composer → clears draft
- idle → `die()` → `process.exit(0)` → summary prints

If the summary stops appearing, the VERIFIED cause (code identical across
0.16.0 → 0.18.2) is the fresh-launch short-sid bug: gateway `session.create`
returns `sid = uuid.uuid4().hex[:8]` (e.g. `a8b0df67`), the TUI's `newSession`
writes THAT short sid to the active-session temp file, but the DB row only
exists under the full key (`20260808_HHMMSS_xxxxxx`) → `db.get_session` exact-
match miss → silent `return` (exit code is already 0, so nothing to catch).
Resumed sessions (`-c`, `--resume`, `/resume`) write the full key
(`r.resumed`/`r.session_key`) and DO print stats. Workaround: launch with `-c`
or quit from a resumed session; upstream fix = TUI should write
`r.stored_session_id ?? r.session_id`. A secondary, circumstantial cause is
Node dying via OS signal (SIGINT during a raw-mode drop) — `subprocess.call`
then returns a negative code and the summary is skipped. Manual check against
real data:
`python3 -c "from hermes_cli.main import _print_tui_exit_summary; _print_tui_exit_summary(None, None)"`

Pitfall: a nested-PTY repro via the terminal tool's raw pty does NOT work — the
`zsh -lic set +m;` wrapper breaks raw-mode input delivery. It DOES work wrapped
in `script -q -f -c "hermes --tui" /tmp/out.txt`; send `/quit` then `\r` (raw
mode needs CR — `submit`'s `\n` is NOT Enter) — the typescript file captures
the post-exit epilogue that the pty preview drops. Exit code 0 + no epilogue in
the typescript = confirmed repro.
Full diagnostic recipe: references/exit-summary-diagnostics.md

## Sources

- https://hermes-agent.nousresearch.com/docs/user-guide/tui (Configuration section)
- https://hermes-agent.nousresearch.com/docs/user-guide/cli (display modes, tool_preview_length)
- Verified Aug 2026; user's machine already has `display.tool_progress: verbose` set
