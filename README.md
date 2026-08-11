<p align="center">
  <img src="https://img.shields.io/badge/Hermes%20Agent-harness-7c3aed?style=for-the-badge&logo=python&logoColor=white" alt="Hermes Agent harness"/>
  <img src="https://img.shields.io/badge/plugins-4-22c55e?style=for-the-badge" alt="4 plugins"/>
  <img src="https://img.shields.io/badge/skills-47-0ea5e9?style=for-the-badge" alt="47 skills"/>
  <img src="https://img.shields.io/badge/scripts-10-f59e0b?style=for-the-badge" alt="10 scripts"/>
  <img src="https://img.shields.io/badge/license-GPLv3-ef4444?style=for-the-badge" alt="GPLv3"/>
</p>

<h1 align="center">agent-skillz</h1>

<p align="center">
  <b>The personal harness for my <a href="https://hermes-agent.nousresearch.com">Hermes Agent</a> setup</b><br/>
  Plugins · Skills · Scripts — battle-tested on a Windows 11 + WSL2 + AMD Ryzen AI NPU machine,
  evolved through months of real daily use.
</p>

<p align="center">
  <a href="#-plugins">Plugins</a> ·
  <a href="#-skills">Skills</a> ·
  <a href="#-scripts">Scripts</a> ·
  <a href="#-getting-started">Getting started</a> ·
  <a href="#-maintaining-this-repo">Maintaining</a> ·
  <a href="#-license">License</a>
</p>

---

A living collection of everything that makes my agent setup actually *mine*:

- **🧩 Plugins** — runtime hooks and tools that extend the agent itself (token budgeting, on-demand NPU inference, full session logging).
- **📚 Skills** — the accumulated procedural knowledge of how to run, fix, and tune this specific machine: Windows internals, GPU gaming, NPU acceleration, ML workflows.
- **🛠 Scripts** — standalone utilities the agent (or you) can call directly.

Everything here was built to solve a real problem, documented so it stays maintainable, and checked in so nothing gets lost between reinstalls. **The rule of this repo: if a harness or tool works, it lives here.**

## ✨ Highlights

| | |
|---|---|
| 🪙 **$0 cloud cost for local inference** | `gemma-npu` runs Gemma 4 on the Ryzen AI NPU — every summarize/classify/vision call offloaded from the API bill, with savings accounted for |
| 🔋 **NPU on demand** | `flm-lifecycle` boots the local inference server only when an NPU tool is called and kills it when the last session ends — zero idle waste |
| 📊 **Every dollar tracked** | `budget-tracker` estimates cost with Hermes' pricing engine (cache-aware), pulls the real DeepSeek balance, and enforces a budget ceiling |
| 🕵️ **Total session recall** | `chat-logger` records every API call, tool invocation, and response as compressed JSON-lines, queryable via CLI |
| 🧠 **45+ skills of hard-won knowledge** | From DWM MPO corruption fixes to DLSS DLL audits to Harbor present-stalls — every fix is a documented playbook, not a memory |
| 🔒 **Privacy by construction** | No logs, session data, or runtime state is ever committed; the `.gitignore` enforces it |

## 📦 Plugins

Runtime extensions for Hermes. Each has its own README with architecture, hooks, and CLI docs.

| Plugin | What it does | Hooks / Tools | Docs |
|---|---|---|---|
| **[budget-tracker](plugins/budget-tracker/)** | Token usage & cost tracking per session, cache-aware estimation, live DeepSeek balance, budget ceiling with progress bar | `on_session_start`, `post_api_request`, `on_session_end` | [README](plugins/budget-tracker/README.md) |
| **[flm-lifecycle](plugins/flm-lifecycle/)** | On-demand FLM NPU server lifecycle — up when an NPU tool is called, down when the last session ends; crash/orphan reconciliation | `on_session_start`, `pre_tool_call`, `on_session_end` | [README](plugins/flm-lifecycle/README.md) |
| **[gemma-npu](plugins/gemma-npu/)** | 7 NPU-accelerated tools (summarize, classify, extract, image analysis, planning) on the `npu` toolset — zero API cost | `summarize_text`, `summarize_document`, `extract_from_webpage`, `classify_text`, `extract_json`, `analyze_image`, `create_plan` | [README](plugins/gemma-npu/README.md) |
| **[chat-logger](plugins/chat-logger/)** | Full-fidelity session recorder — API requests/responses, tool calls with args & results, gzip-compressed JSON-lines | `on_session_start`, `pre/post_api_request`, `pre/post_tool_call`, `on_session_end` | [README](plugins/chat-logger/README.md) |

These four compose into a coherent system:

```
                 ┌──────────────┐
   NPU tool call │ flm-lifecycle │  starts FLM server (on demand)
                 └──────┬───────┘
                        ▼
                 ┌──────────────┐     ┌──────────────────┐
                 │  gemma-npu   │────▶│ FLM + Gemma 4 E4B │  local inference, $0
                 └──────┬───────┘     └──────────────────┘
                        │ token/cost payload
                 ┌──────▼───────┐     ┌──────────────────┐
                 │ chat-logger  │     │  budget-tracker  │  cost + NPU savings
                 └──────────────┘     └──────────────────┘   + DeepSeek balance
```

## 📚 Skills

Procedural knowledge, organized the same way Hermes organizes it — one directory per skill, each with a `SKILL.md` (and references/scripts where the problem demanded them).

### devops · 17

| Skill | What it's for |
|---|---|
| [amd-npu](skills/devops/amd-npu/) | Detect, validate, and use the AMD Ryzen AI NPU (XDNA/XDNA2) |
| [flm-lifecycle](skills/devops/flm-lifecycle/) | Manage the FLM NPU server lifecycle (sessions, ports, models) |
| [context-hub-api-docs](skills/devops/context-hub-api-docs/) | Pull current API docs via Andrew Ng's Context Hub (`chub`) |
| [hermes-browser](skills/devops/hermes-browser/) | Configure and use Hermes' browser automation |
| [hermes-desktop-app](skills/devops/hermes-desktop-app/) | Configure and use the Hermes Desktop app |
| [hermes-plugin-development](skills/devops/hermes-plugin-development/) | Build hook-based Hermes plugins |
| [hermes-tui-configuration](skills/devops/hermes-tui-configuration/) | Configure the Hermes TUI surface |
| [hermes-voice-mode](skills/devops/hermes-voice-mode/) | Set up and troubleshoot Hermes voice mode |
| [local-web-crawler](skills/devops/local-web-crawler/) | Local web crawling with crawl4ai — no API keys |
| [mcp-windows-automation](skills/devops/mcp-windows-automation/) | Windows desktop + browser automation (winappcli + UIA) |
| [playnite-theme-development](skills/devops/playnite-theme-development/) | Playnite fullscreen theme modding (.pth) |
| [python-venv-hygiene](skills/devops/python-venv-hygiene/) | Python environment topology — which interpreter, when |
| [third-party-app-diagnostics](skills/devops/third-party-app-diagnostics/) | Diagnose third-party app memory/resource behavior |
| [windows-debloating](skills/devops/windows-debloating/) | Identify and disable unnecessary Windows services/processes |
| [windows-software-management](skills/devops/windows-software-management/) | Install/manage Windows software from WSL |
| [wsl-resource-tuning](skills/devops/wsl-resource-tuning/) | Tune WSL2 memory/CPU/disk via .wslconfig |
| [wsl-voice-audio](skills/devops/wsl-voice-audio/) | Microphone/speaker audio in WSL (WSLg → Pulse) |

### windows · 4

| Skill | What it's for |
|---|---|
| [asus-rog-power-thermal](skills/windows/asus-rog-power-thermal/) | Power/thermal diagnosis on ASUS ROG laptops |
| [glazewm-configuration](skills/windows/glazewm-configuration/) | Configure and tune the GlazeWM tiling window manager |
| [windows-bluetooth-audio](skills/windows/windows-bluetooth-audio/) | Diagnose Bluetooth audio quality collapse |
| [windows-debugging](skills/windows/windows-debugging/) | Esoteric Windows bugs and proven fixes |

### windows-gaming · 10

| Skill | What it's for |
|---|---|
| [crack-emulator-save-migration](skills/windows-gaming/crack-emulator-save-migration/) | Migrate saves when a repack updates |
| [dlss-management](skills/windows-gaming/dlss-management/) | Scan games for DLSS DLLs, map versions to games |
| [dlss-manager](skills/windows-gaming/dlss-manager/) | Update a game's DLSS DLLs (SR, frame gen, ray reconstruction) |
| [game-dlss-audit](skills/windows-gaming/game-dlss-audit/) | Audit installed games across drives for DLSS DLLs |
| [game-save-recovery](skills/windows-gaming/game-save-recovery/) | Recover saves when they stop loading |
| [playnite-plugin-discovery](skills/windows-gaming/playnite-plugin-discovery/) | Discover/evaluate/install Playnite plugins |
| [rtss-overlay-configuration](skills/windows-gaming/rtss-overlay-configuration/) | RTSS / MSI Afterburner overlay config |
| [rutor-game-search](skills/windows-gaming/rutor-game-search/) | rutor.info search → magnet → qBittorrent |
| [streaming-display-corruption](skills/windows-gaming/streaming-display-corruption/) | Fix display corruption after game-mode switches |
| [windows-gaming-fullscreen-corruption](skills/windows-gaming/windows-gaming-fullscreen-corruption/) | Fix fullscreen exclusive mode corruption |

### ml-agents · 5

| Skill | What it's for |
|---|---|
| [arc-agi-3](skills/ml-agents/arc-agi-3/) | ARC-AGI-3 agent development (game state, FMs) |
| [cloud-gpu-cost-analysis](skills/ml-agents/cloud-gpu-cost-analysis/) | Compare cloud GPU pricing across providers |
| [cloud-gpu-provisioning](skills/ml-agents/cloud-gpu-provisioning/) | Research and provision cloud GPU instances |
| [local-voice-ai-stack](skills/ml-agents/local-voice-ai-stack/) | Design a local voice AI stack for this machine |
| [planning-mode](skills/ml-agents/planning-mode/) | Decompose complex goals with `create_plan` |

### productivity · 5

| Skill | What it's for |
|---|---|
| [conference-paper-discovery](skills/productivity/conference-paper-discovery/) | Find/verify/cite accepted papers at ML conferences |
| [hermes-self-maintenance](skills/productivity/hermes-self-maintenance/) | Scheduled cron jobs that audit and prune |
| [paper-study-notes](skills/productivity/paper-study-notes/) | Study an arXiv paper → notes in the vault |
| [playnite-theme-plugin-integration](skills/productivity/playnite-theme-plugin-integration/) | Playnite fullscreen themes + plugin integration |
| [research-paper-notes](skills/productivity/research-paper-notes/) | Study/summarize/take notes on papers |

### Specialized · 6

| Skill | Category | What it's for |
|---|---|---|
| [harbor-stremio-client](skills/streaming/harbor-stremio-client/) | streaming | Troubleshoot/tune Harbor (4K HDR → mpv) |
| [nextjs-personal-site](skills/web-dev/nextjs-personal-site/) | web-dev | Maintain the Next.js + Tailwind personal site |
| [windhawk-windows-ui-customization](skills/windhawk-windows-ui-customization/) | windhawk | Configure Windows UI via Windhawk mods |
| [windows-computer-use](skills/windows-computer-use/) | computer-use | Windows desktop automation via winappcli + UIA |

### 🗄 Archive

Retired playbooks kept for reference: [`skills/.archive/`](skills/.archive/) — `glazewm-configuration-troubleshooting`, `hermes-acp-editor`.

## 🛠 Scripts

Standalone utilities. WSL scripts live in [`scripts/`](scripts/), Windows PowerShell ones in [`scripts/windows/`](scripts/windows/).

| Script | What it does |
|---|---|
| [research.py](scripts/research.py) | NPU-assisted multi-source research → `crawl_sessions/<slug>/` (summary, synthesis, stats) |
| [dlss_manager.py](scripts/dlss_manager.py) | DLSS DLL update manager (super resolution, frame gen, ray reconstruction) |
| [rutor-search.py](scripts/rutor-search.py) / [.sh](scripts/rutor-search.sh) | rutor.info torrent search → magnet link |
| [flight-search.py](scripts/flight-search.py) | Flight search automation (paired with the windows-computer-use skill) |
| [cdp-bridge.py](scripts/cdp-bridge.py) | Chrome DevTools Protocol bridge for browser automation |
| [vision_gemma4.py](scripts/vision_gemma4.py) | Vision helper for local Gemma 4 inference |
| [windows/rutor-search.ps1](scripts/windows/rutor-search.ps1) | Windows-side rutor search (winappcli-friendly) |
| [windows/check-focus.ps1](scripts/windows/check-focus.ps1) | Focus Assist / quiet-hours status |
| [windows/hermes-notify.ps1](scripts/windows/hermes-notify.ps1) | Windows toast notification bridge for Hermes |

## 🚀 Getting started

```bash
git clone git@github.com:rajatkb/agent-skillz.git
cd agent-skillz

# Plugins → Hermes plugins dir (enabled automatically)
cp -r plugins/* ~/.hermes/plugins/

# Skills → Hermes skills dir (loaded automatically by name)
cp -r skills/devops skills/windows skills/windows-gaming \
      skills/ml-agents skills/productivity skills/streaming \
      skills/web-dev skills/windhawk-windows-ui-customization \
      skills/windows-computer-use ~/.hermes/skills/

# Scripts → wherever you keep agent scripts (~/.hermes/scripts)
cp scripts/*.py scripts/*.sh ~/.hermes/scripts/
mkdir -p ~/.hermes/scripts/windows && cp scripts/windows/*.ps1 ~/.hermes/scripts/windows/
```

Then run `hermes` and check the plugin hooks fired:

```bash
hermes budget          # budget-tracker: shows token/cost totals
hermes chat-log list   # chat-logger: lists recorded sessions
```

### Dependencies

- **Hermes Agent** (pip-installable) — everything here extends it
- **FLM** ([fastflowlm.com/docs](https://fastflowlm.com/docs)) + a Gemma 4 model — for `gemma-npu` / `flm-lifecycle`
- **Windows 11 + WSL2** — where the skills were forged (most transfer elsewhere)
- `httpx` for `budget-tracker`; the rest is stdlib

## 🤝 Maintaining this repo

This repo exists so every harness we build survives reinstalls and forgetfulness. The workflow:

1. **New plugin / skill / script** → build it in `~/.hermes/…`, prove it works, then mirror it here.
2. **Plugins get a README** — overview, hooks/tools table, CLI, install, files, privacy notes. No README, no merge.
3. **Skills stay faithful** — `SKILL.md` plus any `references/` and `scripts/` the skill depends on.
4. **Runtime state never ships** — `data.json`, `sessions.json`, logs, and `__pycache__` are gitignored. If a harness writes state, keep the state file out of the repo.
5. **Retired skills** go to `skills/.archive/` rather than being deleted.

## 📁 Repository structure

```
agent-skillz/
├── README.md               ← you are here
├── LICENSE                 GPLv3
├── .gitignore              runtime-state hardened
├── plugins/                Hermes plugins (hooks + tools)
│   ├── budget-tracker/     token & cost tracking
│   ├── chat-logger/        full session recorder
│   ├── flm-lifecycle/      NPU server lifecycle
│   └── gemma-npu/          NPU-accelerated tools
├── skills/                 procedural knowledge
│   ├── devops/  windows/  windows-gaming/  ml-agents/
│   ├── productivity/  streaming/  web-dev/
│   ├── windhawk-windows-ui-customization/  windows-computer-use/
│   └── .archive/           retired playbooks
└── scripts/                standalone utilities
    └── windows/            PowerShell helpers
```

## 🔒 Privacy

Session logs, budget counters, and server state are **runtime artifacts** — they never enter this repository. The `.gitignore` blocks `data.json`, `sessions.json`, `last_report.txt`, `*.log`/`*.log.gz`, and `__pycache__` at the plugin level, so a careless `git add .` still can't leak conversation data.

## 📄 License

[GPLv3](LICENSE) — free to use, modify, and share; improvements must stay open.
