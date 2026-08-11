# Flow Launcher Plugin Evaluation — Reminder Plugins

Session findings (Aug 2026). User wanted: reminders that fire a native Windows notification, ideally when back at the desk.

## Verdict

- **QuickTodo** (TrueCrimeDev) — the pick: real native Windows toasts, re-fires until task completed/snoozed.
- **RemindMe** (Yusyuriv) — simpler natural-language, but Flow-internal notifications and untested persistence.

## QuickTodo

- Repo: https://github.com/TrueCrimeDev/Flow.Launcher.Plugin.QuickTodo — v1.5.0, pushed Jul 2026 (actively maintained)
- NOT in the official store manifest → manual install inside Flow:
  `pm install https://github.com/TrueCrimeDev/Flow.Launcher.Plugin.QuickTodo/releases/download/v1.5.0/Flow.Launcher.Plugin.QuickTodo.zip`
  (README also supports `pm install <local-zip-path>`; restart Flow after install)
- Syntax: `td <task> #tomorrow@9am`, `td list overdue`, priorities `!high`/`!l`/`!m`/`!h`, categories `@Work`, recurrence `#daily`, `#every-monday`. Outlook COM integration (`td outlook`, `os` mail search).
- Notifications: `Services/ReminderService.cs` uses `Microsoft.Toolkit.Uwp.Notifications` → native Action Center toasts with sound. >3 due at once → single summary toast. Snooze default 10 min.
- "Remind me when I sit back down" behavior: `TodoStore.GetDueReminders()` returns ALL incomplete, un-snoozed tasks whose due moment passed; the poll timer re-toasts them every tick until completed/snoozed. Default poll interval **60 min** — set lower (e.g. 5 min) in plugin settings for prompt re-fire after returning.
- Requires Flow Launcher running (true of all Flow plugins — they are in-process).

## RemindMe

- Repo: https://github.com/Yusyuriv/Flow.Launcher.Plugin.RemindMe — v1.4.0 (Jan 2026), in store as "Remind Me"
- Syntax: `remind add in 5 minutes to stretch`, `remind 11:30am standup`, `remind 22:30 go to bed`, short form `remind 5m stretch` (opt-in in settings)
- Notifications: `Main.cs` → `_context.API.ShowMsg(...)` plus a custom WPF overlay (`Views/NotificationWindow.xaml`). NOT native Action Center toasts.
- Overdue reminders re-fire on plugin load (Flow restart/login), but persistence across restarts "hasn't been thoroughly tested — don't use for anything important."

## Rejected

- Timer (pivotiiii/flow_launcher_timer) — countdown only, no persistent reminders (hourglass lib)
- MarkdownTodo (YukiGasai) — task list, no reminder toasts
- Todoist (jjw24) / Todos (Or1g3n) — no reminder-toast firing
- Full manifest scan (plugin_api_v2 `plugins.json`) found no other reminder plugins

## Notes

- No Flow plugin triggers on session unlock. "Remind when at desk" ≈ QuickTodo's persistent re-toast loop, or RemindMe's overdue-on-load re-fire. A true unlock trigger = Windows Task Scheduler (trigger: unlock) + script — outside Flow.
- Flow plugin install commands: `pm install <name>` (store), `pm install <path-or-url-to-zip>` (manual); `pm` hotkey opens the plugin manager.
- Manifest fetch: `curl -sL "https://raw.githubusercontent.com/Flow-Launcher/Flow.Launcher.PluginsManifest/plugin_api_v2/plugins.json"` (214KB, all plugins; fields: ID, Name, Description, Author, Version, UrlDownload, UrlSourceCode, LatestReleaseDate).
