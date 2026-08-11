# Windows Context Menu Solutions — Mod Catalog & Findings

## The core question
"Remove 'Show more options' and show ALL items in the modern Win11 fluent menu" — does any Windhawk mod do this?

**No.** Verified against the windhawk.net/mods catalog (search "context menu") and windhawk-mods GitHub discussions.

## Why it doesn't exist
The modern menu's item set is built from Explorer's CommandStore (IExplorerCommand registrations). Classic shell extensions (legacy registry verbs) are hidden behind "Show more options" by design. A mod would have to re-implement menu building rather than unhook the trigger — no one has shipped it.

## Open feature requests (ramensoftware/windhawk-mods)
- Discussion #1915 "Add options to Windows 11 context menu" (May 2025, still open, 3 upvotes) — exactly this ask (transfer items between visible/hidden parts); only reply recommends Nilesoft Shell
- Discussion #1836 "Option to use 'hidden' fluent style 'Show more options' context menu"
- URL pattern: `https://github.com/ramensoftware/windhawk-mods/discussions/<id>`

## Windhawk context-menu mods (full catalog from windhawk.net/mods search)

| Mod | Author | Users | What it does |
|---|---|---|---|
| Classic context menu on Windows 11 | m417z | ~42.7k | Removes "Show more options" by reverting to legacy Win10 menu. Hold Ctrl to temporarily open the NEW menu. The ONLY mod that eliminates the extra click. |
| Dark mode context menus | Mgg Sk | ~62.5k | Dark theme for all win32 menus |
| WinUI Context Menu Animation | crazyboyybs | ~16k | WinUI-style vertical slide animation on classic menus |
| Remove Context Menu Items | Armaninyow | ~4.3k | Remove unwanted items, context-aware filtering |
| Taskbar classic context menu | m417z | ~1.5k | Classic menu for taskbar item right-clicks |
| Disable Immersive Context Menus | ItsProfessional | ~900 | Disables modern menus in File Explorer (→ classic) |
| Context Menu Preloader | Lockframe | ~770 | Preloads/pins context menu handlers into RAM (perf) |

## Alternatives that DO show all items in a modern-styled menu
- **Nilesoft Shell** (nilesoft.org, GitHub nilesoft/shell) — free, open source. Replaces the right-click menu with its own fluent/acrylic-styled menu; ALL items (legacy + modern) merged into one. Loads as a shell-extension DLL into explorer.exe (no separate process, ~few MB). Config file is `shell.nss` — themeable, per-item control. The standard recommendation for the "show more options" complaint (HowToGeek, MUO articles).
  - Caveat: REPLACES Microsoft's menu rather than patching it — rendering is Nilesoft's own (themeable acrylic), so it doesn't literally extend the modern menu.

## Verified non-answers
- StartAllBack's context menu option ("Enable classic full context menus") → classic Win10 menu, NOT modern-menu expansion
- ExplorerPatcher legacy context menu → classic menu
- Registry route: add specific commands to the modern menu via `HKCU\Software\Classes\...\shell` CommandStore-style registration — manual per command, no blanket "show all"

## Technique note
windhawk.net/mods is a JS SPA — curl returns only shell HTML (~1.8KB, empty grep). Use browser_navigate to search the catalog, or web_search with site-restricted queries.
