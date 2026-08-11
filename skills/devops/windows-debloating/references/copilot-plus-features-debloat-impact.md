# Windows 11 25H2 Copilot+ AI Features — Impact of Debloating

Reference: what AI features exist in Windows 11 25H2, whether debloating removes them, and what hardware they require. Helps users make informed trade-off decisions when debloating.

## Feature Matrix

| Feature | Debloat Impact | Requirements | Hardware-gated? | Worth restoring? |
|---------|---------------|-------------|-----------------|-----------------|
| **Recall** | Stripped (WinUtil removes Copilot/AI packages) | NPU 40+ TOPS, 16GB RAM, 256GB SSD | Yes — exclusive to Copilot+ PCs | Only if you want semantic desktop search. Privacy trade-off: screenshots every few seconds stored locally. Open-source alternative: screenpipe / rewritten.dev |
| **Click to Do** (Win+Q) | Stripped (same AI package removal) | NPU 40+ TOPS | Yes — exclusive to Copilot+ PCs | Select any text on screen → summarize/rewrite/bulleted list via local Phi Silica. Image: bg removal, object erase. Each action has a non-AI equivalent in 1-2 more clicks. |
| **Windows Studio Effects** | Not stripped by WinUtil (part of Windows Camera pipeline) | NPU recommended (falls back to GPU/CPU) | No — works on any Windows 11 device | Eye contact, portrait blur, background replacement, auto-framing, voice focus. If you already use NVIDIA Broadcast/OBS filters, these are redundant. |
| **Auto Super Resolution** | Stripped (part of Copilot+ package) | NPU 40+ TOPS | Yes — exclusive to Copilot+ PCs | AI upscaling for games via NPU. Limited game support. Your 5070 Ti's DLSS is strictly better. |
| **Copilot** (system-wide, voice, vision) | Stripped (WinUtil targets Copilot explicitly) | Cloud for heavy tasks, NPU for local Phi Silica | No (cloud), Yes (local NPU features) | General Q&A assistant. Hermes fills this role better on your machine. |
| **Live Captions (AI)** | Not stripped (accessibility feature) | Any | No | Real-time translation of audio to English text. Useful if you watch foreign language content. |
| **File Explorer AI actions** | Stripped (Copilot-dependent) | NPU 40+ TOPS for local, cloud otherwise | Partial | Right-click image → remove background, erase object. Right-click doc → summarize. The individual app actions (Paint bg removal, Photos erase) still work — just the context-menu shortcut is lost. |
| **Clipboard AI search** | Stripped | NPU 40+ TOPS | Yes | Semantic search of clipboard history. Ditto already does this better. |
| **Cocreator** (Paint AI) | App-dependent (Paint app may be uninstalled) | NPU recommended | Partial | Text-to-image in Paint. |
| **Photos Restyle Image / Image Creator** | App-dependent | Cloud for Image Creator, NPU for Restyle | Partial | AI image editing. Midjourney/ComfyUI alternatives exist. |

## Hardware Reality Check

Your laptop: **AMD Ryzen AI 300 series** (50 TOPS NPU) → qualifies as Copilot+ PC. Debloating didn't strip the NPU driver — only the software package. The hardware capability is there.

## If You Want a Feature Back

You don't need to restore the full Copilot+ suite for every feature:

| Want | Minimum path |
|------|-------------|
| **Click to Do** (select-any-text→AI) | Restore via Settings → Windows Update → optional updates, or manually reinstall the Copilot app package. Alternatively, PowerToys Text Extractor (Win+Shift+T) gives you screen OCR to clipboard today. |
| **Recall** alone | Reinstall the Recall package via winget `MicrosoftRecall` or the Store. Or use open-source `screenpipe`. |
| **Just the AI** without Microsoft | Your Hermes/FLM + PowerToys Text Extractor fork covers 90% of Click to Do use cases without telemetry. |

## Key Takeaway for Debloat Decisions

- **Features you genuinely lose**: Recall (no real alternative at OS level), Click to Do convenience (individual actions exist but the unified UX is gone).
- **Features you don't lose**: Studio Effects, Live Captions, basic OCR (Text Extractor is separate).
- **Features with better alternatives**: Copilot → Hermes, Auto SR → DLSS, Cocreator → ComfyUI/Stable Diffusion, Clipboard search → Ditto.
