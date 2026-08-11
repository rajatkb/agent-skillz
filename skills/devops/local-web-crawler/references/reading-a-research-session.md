# Reading a research session folder (user-facing guide)

When a `research.py research` run completes, the user will often ask "what did it find?" or "help me navigate it". The folder is a **layered evidence funnel** — present it top-down by folder number, and always lead with the answer, not the raw data.

## The funnel

```
01_search/     →  "what did we look for"      (raw DDGS results — curiosity read)
02_pages/      →  "what did we download"      (full article text — DON'T lead with this)
03_notes/      →  "what did the pages SAY"    ★ THE EVIDENCE
04_links/      →  "what else looked promising" (frontier — follow-up material)
05_synthesis/  →  "so what's the answer"      ★ THE ANSWER — read this FIRST
06_stats.md    →  "how much did it cost"      (telemetry — curiosity read)
```

## Recommended walkthrough order

1. **`05_synthesis/findings.md`** — the distilled answer. Every claim carries an inline source URL. Lead here.
2. **`03_notes/`** — the evidence layer. Each file:
   - **Bold line** = a fact Gemma extracted
   - **`> quote` line** = the exact source sentence proving it ("the receipt")
   - Header shows `Relevance: <score> — <reason>` (BM25 + DDGS provenance)
   - Point out: if a claim looks wrong, search `02_pages/<same-file>` for the quote to verify against the raw article. Nothing is asserted without a receipt.
   - Quirk: some notes have facts but no numbers (or vice versa) — that's the `has_numbers` gate skipping the numbers pass on digit-free chunks, not a failure.
3. **`02_pages/`** — only to verify a specific quote against the raw crawl.
4. **`00_plan.md` + `01_search/`** — how Gemma decomposed the query and what DDGS returned. Only if curious.
5. **`06_stats.md`** — token/call/wall-time receipt. Only if the user cares about cost.

## How to turn findings into a user answer

The notes answer hardware-specific sub-questions the sources may not state directly. Example: user has a 12GB VRAM GPU; notes say "Qwen 3.6 32B needs 24GB at Q4" + "a 32B at Q3 is worse than a 14B at Q5" → the *derived* answer for 12GB is "smaller model at better quantization (Gemma 9B / Llama 8B tier)" — the folder contains the premises, DeepSeek does the inference. State which parts are quoted facts vs derived conclusions.

## Honesty flags to surface proactively

- `findings.md`'s "Open Questions" section = what the sources did NOT cover. If the user's real question lands there, say so — and offer a re-run with a tighter query or higher budget (session is resumable).
- `session.json` errors list = dead ends hit (JS walls, block pages). Skim it before claiming completeness.
- Budget-stop vs coverage-stop: the loop stops on `--max-pages` (budget), so "DONE" does not mean "exhaustive". If the frontier still has high-scored unvisited links, a re-run with `--max-rounds`/`--max-pages` raised will dig further (resumes from saved state).
