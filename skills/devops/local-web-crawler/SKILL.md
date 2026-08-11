---
name: local-web-crawler
description: Crawl web pages locally using crawl4ai — no API keys, no cloud services. Outputs clean markdown for LLM ingestion, RAG, or offline reading.
---

# Local Web Crawler (crawl4ai)

Uses [crawl4ai](https://github.com/unclecode/crawl4ai) — a 50k+ star open-source Python crawler that turns web pages into LLM-ready markdown. Runs fully local with Playwright.

## When to use

**web_search is the primary tool** — use it first for finding information, getting snippets, and locating relevant pages. The crawler is for the follow-up: when search returns a promising URL and you need the **full page content** (reading a blog post, extracting docs, grabbing all text from a page for analysis).

⚠️ **web_extract is broken on this system** (DDGS backend doesn't support extraction). **Never use web_extract.** Always use this crawler (crawl4ai) or the browser tool for content extraction instead.

- `web_search` = finds the doors (entry point)
- `crawler` = walks through them (content retrieval)

Don't reach for the crawler as a search replacement — it's a content-retrieval tool for URLs already identified as relevant.

### USER CORRECTION (Aug 2026): use `research.py research` PROACTIVELY for multi-source questions

The user called this out explicitly after I defaulted to repeated `web_search` + `extract_from_webpage` for a multi-source synthesis question ("You did not use the research crawler we have implemented why explain?"). This governs the class of task now:

- **Multi-source synthesis questions** ("what are the recommended X for Y", "compare options for Z", "best settings for...") → go straight to `research.py research "<question>"`, NOT a web_search loop. It refines → searches → fetches → quote-anchored notes → synthesis, all on the local NPU at zero API cost, and sidesteps 403/fingerprint blocks (crawl4ai fetches with a real browser).
- **Single-fact lookups** ("what version is X", "does Y exist") → `web_search` first is fine.
- **Single known URL needing full content** → `research.py fetch <url>` or the curl+NPU fallback above.
- When a `web_search`/`extract_from_webpage` attempt hits 403 or the topic turns out deeper than a snippet, **escalate to `research.py research`** instead of hammering more searches.

Session evidence: the DLSS 4K settings run (4 rounds, 24 pages, 172K tokens on NPU, ~35 min) produced a synthesis with open-questions tracking that ad-hoc searches never would — and its `05_synthesis/findings.md` correctly reported "no official per-game recommendations exist" as a verified negative instead of an assumption.

### `extract_from_webpage` (NPU tool) 403s on some sites — curl fallback

The gemma-npu `extract_from_webpage` tool fetches with plain `urllib` (no custom User-Agent), so sites with basic bot filtering (e.g. benchlm.ai, gemma4.online) return `HTTP 403`. The tool returns `{"error": ...}` — harmless but contentless. Fix pattern (verified): fetch with a browser UA and feed the text to the NPU tools instead:

```bash
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
curl -sL -A "$UA" -o /tmp/page.html --max-time 20 "<url>"
# strip to text: python3 -c "import re,html;t=re.sub(r'<(script|style)[^>]*>.*?</\1>',' ',open('/tmp/page.html').read(),flags=re.DOTALL|re.I);print(html.unescape(re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',t))).strip())" > /tmp/page.txt
# then summarize_text / extract_json on the text (still NPU, still tracked)
```

The browser-UA curl got 200s from all three sites that 403'd the tool. Note `web_extract` is search-only on this system, so curl is the cheapest middle path between the NPU tool and the full browser.

## What NOT to use: web_extract

**On this system, `web_extract` is broken** — the configured backend (DuckDuckGo) does not support URL content extraction. It throws `DuckDuckGo (ddgs) is a search-only backend and cannot extract URL content`.

**Replacement options in priority order:**
1. **crawl4ai** (this skill) — best for full-page markdown extraction, docs, blog posts, any URL
2. **Browser tools** — use `browser_navigate` + `browser_snapshot(full=true)` for JS-heavy SPAs or pages needing interaction before content appears

**To surgically remove `web_extract` from Hermes' tool list** (so it stops appearing as an available tool):

```bash
# Patch toolsets.py — removes "web_extract" from the core tool list
# and from the "web" toolset definition
python3 -c "
import re
path = '/home/rajat-g14/.asdf/installs/python/3.11.0/lib/python3.11/site-packages/toolsets.py'

with open(path) as f:
    content = f.read()

# Remove from _HERMES_CORE_TOOLS
content = content.replace(
    '\"web_search\", \"web_extract\",',
    '\"web_search\",'
)
# Remove from TOOLSETS[\"web\"]
content = content.replace(
    '\"tools\": [\"web_search\", \"web_extract\"],',
    '\"tools\": [\"web_search\"],'
)

with open(path, 'w') as f:
    f.write(content)

print('Done. web_extract removed from toolsets.py')
"
```

This modification gets reverted on Hermes upgrades — re-apply after `pip install --upgrade hermes-agent`. See `references/disable-web-extract.md` for a standalone re-runnable script.

**Alternative: use the `search` toolset** instead of `web`. The `search` toolset is already defined in `toolsets.py` and only contains `web_search` (no `web_extract`).

## Setup

```bash
pip install crawl4ai
python -m playwright install chromium   # one-time browser download
```

Already installed on this system. Playwright chromium is cached.

**Where crawl4ai lives (important for venv hygiene):** crawl4ai + playwright are installed in the **Hermes runtime** (`~/.asdf/installs/python/3.11.0/lib/python3.11/site-packages`), NOT in any venv — research.py's `#!/usr/bin/env python3` shebang resolves to the asdf runtime interpreter. Do NOT pip-install crawl4ai into the agent venv; if the runtime ever needs it reinstalled, use `env -u PYTHONPATH <venv>/bin/pip install crawl4ai` and verify `python -m playwright install chromium`. Note: the Hermes TUI exports PYTHONPATH pointing at the runtime site-packages, so venv pythons can `import crawl4ai` from the runtime even though it isn't installed in them (see python-venv-hygiene skill).

## Usage

Single entry point: `~/.hermes/scripts/research.py` with two subcommands — `fetch` (one-shot) and `research` (deep Gemma loop).

### fetch — one-shot page fetch (no Gemma, no loop)

```bash
python3 ~/.hermes/scripts/research.py fetch https://example.com
python3 ~/.hermes/scripts/research.py fetch https://a.com https://b.com -o output.md
python3 ~/.hermes/scripts/research.py fetch https://docs.example.com --bm25 --query "setup guide"
```

Options:
- `-o <file>` — write to file
- `--no-prune` — raw markdown, no filtering
- `--bm25 --query "terms"` — keyword-aware content filtering
- `--verbose` — show crawl4ai logs
- `--no-headless` — show browser window for debugging

### From execute_code (Python)

```python
from hermes_tools import terminal

# Crawl a page → markdown
result = terminal(f"python3 ~/.hermes/scripts/research.py fetch https://example.com")
markdown = result["output"]
```

Or use crawl4ai directly for more control — **NOTE: on crawl4ai 0.9.x, `content_filter` is a settable attribute, NOT a constructor kwarg** (passing it in `CrawlerRunConfig(...)` crashes with `TypeError: unexpected keyword argument`):

```python
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai.content_filter_strategy import PruningContentFilter

async def crawl(url: str) -> str:
    cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
    cfg.content_filter = PruningContentFilter(threshold=0.48, threshold_type="dynamic")  # set AFTER construction
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url, config=cfg)
        return result.markdown if result.success else result.error_message
```
### Deep crawling (follow sub-pages)

The `fetch` subcommand only does single-page fetches. For multi-page crawling that follows links, use crawl4ai directly with a deep crawl strategy:

```python
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, BestFirstCrawlStrategy, DFSCrawlStrategy
from crawl4ai.content_filter_strategy import PruningContentFilter

async def deep_crawl(start_url: str, max_depth: int = 2, max_pages: int = 50):
"""BFS — breadth-first: follow all links at each depth level before going deeper."""
strategy = BFSDeepCrawlStrategy(
max_depth=max_depth,
max_pages=max_pages,
include_external=False,      # stay on same domain
score_threshold=0.3,         # minimum link relevance score
)
config = CrawlerRunConfig(
deep_crawl_strategy=strategy,
cache_mode=CacheMode.BYPASS,
verbose=True,
)
config.content_filter = PruningContentFilter(threshold=0.48, threshold_type="dynamic")  # 0.9.x: set as attribute
async with AsyncWebCrawler() as crawler:
result = await crawler.arun(url=start_url, config=config)
return result.markdown if result.success else result.error_message

# Alternative: BestFirstCrawlStrategy — priority-queue, scores links by BM25 relevance
# strategy = BestFirstCrawlStrategy(max_pages=30, include_external=False)

# Alternative: DFSCrawlStrategy — depth-first, follows one branch at a time
# strategy = DFSCrawlStrategy(max_depth=2, max_pages=30)
```

## Advanced features available in crawl4ai

- **Deep crawling** — follow links to a depth/breadth limit for full site extraction
- **Structured extraction** — CSS/XPath selectors, JSON schemas, LLM-based extraction
- **Screenshots** — capture page screenshots during crawl
- **Session reuse** — login flows, pagination, multi-step navigation
- **Cache modes** — ENABLED, BYPASS, DISABLED for dev vs prod

See [docs.crawl4ai.com](https://docs.crawl4ai.com/) for the full SDK reference.

## Ranking & Scoring Results

crawl4ai has built-in relevance ranking at two levels:

### 1. Within-page content ranking (BM25ContentFilter)

Filters out irrelevant paragraphs/sections from a single page's markdown using BM25 scoring against a query. Already exposed via `--bm25 --query "terms"` in `research.py fetch`.

### 2. Cross-link scoring (LinkPreviewConfig + score_links)

When crawling a doc page with many links, crawl4ai fetches head content from each link and scores them:

```python
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, LinkPreviewConfig

config = CrawlerRunConfig(
    link_preview_config=LinkPreviewConfig(
        include_internal=True,
        max_links=20,
        query="your search topic",       # BM25 contextual scoring
        score_threshold=0.3,             # filter low-relevance links
        concurrency=5,
    ),
    score_links=True,
)
async with AsyncWebCrawler() as crawler:
    result = await crawler.arun("https://example.com", config=config)
    for link in result.links["internal"]:
        print(f"{link['total_score']:.3f} - {link['href']}")
```

Three score types per link:
- **Intrinsic (0–10)** — URL quality, link text meaningfulness
- **Contextual (0–1)** — BM25 relevance against query text
- **Total** — weighted combination (intrinsic falls back when contextual unavailable)

### 3. Optional: Semantic reranking via NPU embeddings (advanced)

If FLM is running with `--embed 1` (loads `embed-gemma:300m` alongside the LLM), add post-crawl semantic reranking:

```python
from openai import OpenAI
import numpy as np

client = OpenAI(base_url="http://172.29.192.1:50001/v1", api_key="flm")

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

query_vec = client.embeddings.create(
    model="embed-gemma", input=["your query"]
).data[0].embedding

for chunk in chunks:
    vec = client.embeddings.create(
        model="embed-gemma", input=[chunk["text"]]
    ).data[0].embedding
    chunk["semantic_score"] = cosine_similarity(query_vec, vec)

chunks.sort(key=lambda x: x["semantic_score"], reverse=True)
```

**Recommended pipeline:**
1. `web_search` finds candidate URLs
2. crawl4ai `LinkPreview` + BM25 scores ranks links (fast, no extra infra)
3. Crawl top-K links for full content
4. Optional: FLM embeddings rerank content chunks semantically (requires `--embed 1`)

See `references/flm-embedding-reranking.md` for a reusable script.

## Anti-hallucination design (Gemma layer)

The Gemma layer is **extraction-only, quote-anchored** — designed to minimize small-model confabulation:

- **FACT_SYSTEM**: extracts facts as JSON `[{fact, quote}]` — every fact MUST carry its verbatim source quote. No inference, no estimation; absent = absent.
- **NUMBER_SYSTEM**: separate pass for numeric claims `[{value, unit, context}]` — numbers get special handling because they're the most confabulated token class.
- **No merge step**: chunked page → per-chunk fact/number lists → note. The old "merge section summaries" step was a 4th compression where gaps got filled; it's gone.
- **RANK_SYSTEM (now EXTRACT-only)**: URLs must appear VERBATIM in page content; Gemma outputs `[{url, title, anchor, context}]` with NO scores — BM25 scores links afterwards. `add_links` has a scheme guard (`www.amd.com` → `https://www.amd.com`) because Gemma emits bare domains.
- **SYNTH_SYSTEM**: every claim must trace to a quoted fact + source URL; explicit contradiction handling; "evidence is thin" honesty clause.
- **Temperature**: extraction at 0.1 (near-greedy), query refinement at 0.5 (creativity wanted).
- **Truncation tolerance**: `extract_json()` repairs truncated JSON (strips trailing comma, closes dangling arrays) and extraction max_tokens are generous (facts 2000, numbers 1200) — FLM at 800 tokens truncates mid-array.

## Mechanical pre-pruning (the real token saver — Aug 2026)

**Never feed raw page text to Gemma.** `prune_relevant(content, query)` runs before any LLM call and keeps only text blocks containing ≥1 query keyword (word-boundary regex, stopwords stripped) or headings, capped at `MAX_PAGE_EXTRACT_CHARS` (default 25K). Pure Python — zero NPU cost.

Measured on the same 195KB notebookcheck page (gemma4-it:e2b):

| Metric | RAW (old) | PRUNED (new) |
|---|---|---|
| NPU calls | 9 | 4 |
| Prompt tokens | 98,496 | 34,990 (**-64%**) |
| Completion tokens | 7,964 | 4,275 |
| Wall time | 718.8s | 313s (**-56%**) |
| Facts extracted | 13 | 13 (same quality) |

Additional levers, all in `summarize_page`:
- `has_numbers(chunk)` gate — the NUMBER_SYSTEM pass only runs on chunks containing digits (skips ~half the calls on prose pages)
- Tighter max_tokens: facts 1500, numbers 900
- `extract_links` also prunes (max 18K) before asking Gemma for link candidates — the extractor sees the same on-topic text.

## Ranking: BM25 + DDGS positional prior, Gemma steers only (IMPLEMENTED Aug 2026)

User's workflow correction for the research loop's ranking — **implemented and live in research.py**:

1. **DDGS rank IS used — as a positional prior, not ignored.** User corrected the initial "DDGS has no opinion" design: `ddgs_search()` records `ddgs_rank` per result (1 = best), and `rank_candidates()` blends `final = 0.6·bm25_norm + 0.4·(1/(rank+2))`. DDGS order breaks BM25 ties, but content match dominates.
2. **BM25 reverse-index is the primary ranker** — deterministic, pure Python, zero NPU cost. `BM25Index` class (k1=1.5, b=0.75): build term→postings over candidate text (title+snippet for search hits, anchor+title+context for in-page links), score against query terms. `rank_candidates()` seeds the frontier; `score_discovered_links()` scores links Gemma extracted, with a 30% parent-provenance prior (`PARENT_WEIGHT`).
3. **Gemma never ranks** — `extract_links()` (renamed from `rank_links`) pulls `{url, title, anchor, context}` from a page with NO scores; BM25 scores them afterwards. RANK_SYSTEM prompt is now extraction-only ("Do NOT score links").
4. **Gemma steers the top slice ONCE per round** — `steer_frontier()` takes the top `--gemma-rank-top` unvisited items (default 10; DeepSeek/Hermes decides per call) and returns `visit | priority | skip` verdicts: priority → +1.5 score, skip → removed from frontier, visit → unchanged. Gemma never sees the whole frontier and never scores >10 items.
5. Deterministic steps (BM25, dedup, domain filter, scheme guard) all run BEFORE any Gemma call.

**Observed effect (live run):** frontier seeds carry visible provenance (`bm25=1.0 ddgs=0.3333`), source diversity improved (4 pages from 4 different domains vs old run's 2-domain echo), and steering measurably re-ranked the frontier (5 priorities, 4 skips applied).

Tunables: `BM25_K1`, `BM25_B`, `BM25_WEIGHT` (0.6), `PARENT_WEIGHT` (0.3) env vars; `--gemma-rank-top` CLI.

Full design spec + coverage gate: `references/ranking-and-coverage-design.md`.

**Implemented follow-ups (Aug 2026) — do NOT re-derive:**
1. **Content-preview ranking (A)**: `rank_with_content()` fetches each candidate's head content via lean HTTP (`content_preview()`, capped `CONTENT_PREVIEW_CHARS=20000`), BM25-indexes the ACTUAL text, falls back to title+snippet only for unfetchable pages (`content_scored` flag). Round 0 and every re-search run through it. Observed: 19/22 candidates content-scored on a live run.
2. **Re-rank fetched pages on real content (B)**: after a successful fetch, the frontier entry's score is replaced with BM25 over the pruned real content (`content_bm25=` appended to `reason`). Provenance now reflects what the page actually said, not what DDGS claimed.
3. **Re-search triggers (C)** — DDGS is now a recurring engine, not a one-shot seed. At each round start: if best unvisited frontier score < `SEARCH_FLOOR` (0.20) OR distinct note domains < `MIN_DOMAINS` (3), and `searches < MAX_SEARCHES` (4), then `gap_query()` (Gemma writes ONE follow-up query given covered domains — the only LLM step in this path) → `ddgs_search()` → content-preview → BM25 rank → merge into frontier (deduped). Observed live: fired twice in one run, merged +6 new candidates the first time, +0 the second (dedup working). Search count persisted in `session.json["searches"]`.

**Known gaps (do not re-derive):**
1. The loop still stops on budget (`--max-pages`), NOT coverage. A run can end with frontier 9/10 links unvisited and only 2 domains read and still report DONE. Planned fix is a `should_stop()` coverage gate: frontier best-score floor (<7), min distinct domains (≥4), fact-yield saturation (<15% new facts vs prior round), open-questions closure. Until implemented, treat budget completion as "paused," not "exhaustive" — re-run the same query (resumes frontier) or raise `--max-rounds/--max-pages`.

## Client-side hang protection (fail-fast on wedged FLM)

FLM can be alive-but-unresponsive after a killed request (see flm-lifecycle skill). A client that retries 3× with 180s timeouts burns **~9 min per call** silently. `research.py` protects itself two ways:
1. **Fail-fast on timeout**: in `gemma_chat_retry`, a `TimeoutError`/`socket.timeout`/`URLError` containing "timed out" raises immediately instead of retrying — a wedged server won't recover within the retry budget.
2. **Liveness probe before work**: `flm_alive()` = `urlopen(FLM_BASE_URL + "/models", timeout=3)` at each round start; abort with a logged FATAL error if dead. `http_fetch` also caps reads at 5MB so a giant page can't OOM the 3.8GB box.

### "Looks hung but is working" — how to tell (observed Aug 2026)

A research round mid-extraction looks dead: Python process at **0% CPU, `sigsuspend` state, 0 open sockets, ~8MB RSS** — that is NOT a hang, it's the process parked between sequential NPU calls (each ~60-90s on gemma4-it:e2b). Distinguish working vs wedged:
- **Working**: FLM's Windows CPU counter keeps climbing — `powershell.exe "Get-Process flm | Select CPU,WorkingSet64"` sampled 10s apart shows increasing CPU seconds. `session.json` shows a stale pre-round state (round N / pages 0) because `save()` fires only at round end — files in `02_pages/` with fresh timestamps confirm progress.
- **Wedged**: FLM CPU flat AND a fresh `curl /v1/models` times out AND a tiny inference (max_tokens=10) hangs. Then the fix is FLM restart, not patience: `flm-down.sh && flm-up.sh <model>`.

**After ANY kill of research.py mid-request, restart FLM before measuring or resuming** — a killed in-flight NPU request can leave the server alive-but-wedged, which produced a false "NPU is slow" diagnosis (300-token request timing out at 120s when the healthy server does 94 tokens in 5.3s). Always re-measure after `flm-down.sh`/`flm-up.sh`.

## Model choice for the research loop (A/B tested Aug 2026)

**Stick with `gemma4-it:e2b` (22.6 tok/s) for the loop.** Tested `llama3.2:1b` (64.5 tok/s, 1.6x faster) — **rejected**: it cannot follow JSON schemas at all (no array brackets, duplicate keys, quote/fact mismatches, ignores max_tokens and line-delimited JSONL variants). The quote-anchored extraction *requires* structured output, and 1B models fail it. The 22.6 tok/s of e2b is the price of reliable extraction. `gemma3:1b`-class models will have the same problem.

Restarting FLM with a different model: `flm-down.sh` → `flm-up.sh <model>`. NPU validation: `powershell.exe "& 'C:\Program Files\flm\flm.exe' validate"` → `NPU: XDNA2`.

## Telemetry (per-run)

`research.py` reports a full usage breakdown at the end (printed + written to `06_stats.md` in the session):
gemma call count, prompt/completion/total tokens, wall time, and **avg decode tok/s measured by FLM** (`decoding_duration`/`decoding_speed_tps` from the usage object). DeepSeek reads `06_stats.md` to judge whether the research scope was adequate or needs a follow-up run. The weighted-average formula is `total_completion_tokens / Σ(completion_tokens/tps)`.

## Memory-lean fetching (critical on this 3.8GB WSL box)

`research.py` is **HTTP-first, browser-only-as-fallback** — OOM safety by design:

1. **Plain HTTP fast path** (`urllib` + bs4 HTML→markdown) — ~35-124 MB peak RSS, no Chromium. Handles ~80% of pages (static HTML, blogs, docs, wiki).
2. **JS-shell detection** — if extracted text < 300 chars AND raw HTML contains SPA markers (`id="root"`, `__NUXT__`, etc.), it falls back to a real browser. Tiny-but-real pages (example.com) do NOT trigger the browser.
3. **Browser fallback** (`crawl4ai`) — only for JS-heavy/failed pages, and always with lean settings: `light_mode=True`, `text_mode=True`, `--disable-gpu`, `--disable-dev-shm-usage`, `--no-sandbox`, `semaphore_count` capped, `page_timeout=30000`. Default `--concurrency 2`.
4. **Crash guard** — `run_safe()` wraps `run()`; any top-level exception (incl. OOM kills) is logged as `FATAL: <type>: <msg>` to `session.json`'s `errors` list instead of dying silently, and re-running the same query resumes from the saved frontier.
5. **Blocked-domain filter** — `ddgs_search()` filters results against `BLOCKED_DOMAINS` (youtube.com, youtu.be, reddit.com, twitter.com/x.com, facebook, instagram, tiktok, twitch, discord, linkedin). These are video walls / hard anti-bot / login-required — plain HTTP gets a block page (Reddit literally returns the text "Reddit", <300 chars → flagged short) and even the browser fallback can't get real content. Without the filter they poison the frontier: demo runs come up empty with "no notes to synthesize". Check `is_blocked_domain()` (exact-or-subdomain match) before adding search hits to the frontier.
6. **Extraction cost cap** — `MAX_PAGE_EXTRACT_CHARS=25000` (env-overridable) + `prune_relevant()` keyword pre-filter (see "Prune BEFORE extraction" section — the 64% token cut). The cap bounds per-page extraction cost; the raw page is still saved in full to `02_pages/` (only the Gemma extraction input is truncated).

Budget defaults are lean: `--pages-per-round 2` (was 6), `--concurrency 2` (was 6). If a page returns a "Please wait while your request is being verified" interstitial, the site is behind a JS challenge — neither path can bypass it; it's a dead link for our purposes.

## Autonomous research loop (research.py research)

`research.py research "query"` runs the full loop: **Gemma refines query → DDGS searches → content-preview + BM25+DDGS ranks frontier (deterministic) → crawl4ai fetches → Gemma extracts facts (quote-anchored) + extracts links (no scores) → BM25 scores links + re-ranks fetched pages on real content → Gemma steers top-10 once per round → re-search trigger on weak frontier/low diversity → synthesis**. No DeepSeek/API tokens spent on the loop — everything runs on the local NPU (FLM) + ddgs + crawl4ai. **For deep multi-source dives, prefer this over repeated `fetch` calls.**

```bash
python3 ~/.hermes/scripts/research.py research "your research question" \
  --max-rounds 3 --pages-per-round 2 --max-pages 10 --gemma-rank-top 10 \
  --model gemma4-it:e2b            # e4b = slower, better quality; lean defaults are safe on this 3.8GB box
```

- Session tree at `~/.hermes/crawl_sessions/<slug>/` — **DeepSeek reads `03_notes/` + `05_synthesis/findings.md`** (compressed per-page notes + final synthesis), never raw pages.
- State in `session.json` — **resumable**: re-run same query to continue the frontier.
- Config via env: `FLM_BASE_URL`, `FLM_MODEL`, `DDGS_DELAY`, `GEMMA_CHUNK_CHARS`, `MAX_PAGE_EXTRACT_CHARS`, `BM25_K1`, `BM25_B`, `BM25_WEIGHT`, `PARENT_WEIGHT`, `CONTENT_PREVIEW_CHARS`, `SEARCH_FLOOR`, `MIN_DOMAINS`, `MAX_SEARCHES`.
- **Presenting results to the user**: users read the session folder like a funnel — `05_synthesis/findings.md` (answer) FIRST, then `03_notes/` (evidence, bold claim + blockquote receipt per fact), then `02_pages/` only to verify a quote against the raw article. `00_plan.md`/`01_search/`/`06_stats.md` are curiosity reads. When the user asks "what did it find / help me navigate", walk this order and point out that every bold claim in a note has its verbatim `> quote` receipt right under it — that's the anti-hallucination guarantee made visible. See `references/reading-a-research-session.md`.
- **DDGS pitfall**: use `from ddgs import DDGS` (new package name) with `backend="auto"`. The old `duckduckgo_search` import path returns 0 results (broken default backend). `backend="bing"` is the fallback.
- **Dedup**: `round_links` must filter against `sess.state["visited"]` (live state), NOT a local set captured at startup — a stale local set re-fetches already-visited URLs.
- **Scheme-less URLs from the link-extractor**: Gemma's `extract_links` sometimes emits bare domains (`www.amd.com`) without a scheme. crawl4ai then crashes with `ValueError: URL must start with 'http://', 'https://', 'file://', or 'raw:'` — it fails the whole round. Guard in `add_links`/`norm_url`: `if not u.startswith(("http://", "https://")): u = "https://" + u`.
- **Small-model hallucination in synthesis**: `findings.md` can contain fabricated statistics with plausible-looking sources (observed: `$12.9$ tokens/s` attributed to a `localscore.ai` that never appears in the notes — LaTeX-escaped numbers are a tell). Add an explicit "no invented stats; only facts present in the notes" line to SYNTH_SYSTEM, and cross-check numbers against `03_notes/` before trusting findings.
- **Silent mid-run death on low-RAM WSL**: this box has 3.8 GB RAM total. FLM server + crawl4ai Chromium + the Python loop can OOM-kill with NO error in `session.json` and no dmesg trace (Hyper-V reclaims at host level, guest never logs it). Signature: process gone, `session.json` shows pre-round state (round N / pages 0) because `save()` only fires at round end. Mitigations: (1) `--pages-per-round 2` on memory-constrained boxes; (2) after a silent death, just re-run the same query — the session is resumable, though pages visited in the killed round get re-fetched (their state wasn't persisted). Crash guard exists: `run_safe()` wraps `run()` and logs `FATAL: <type>: <msg>` to `session.json` on any top-level exception (incl. OOM kills) — check `session.json`'s `errors` list first when a run dies without output.

## Pitfalls

- **Steam store: `/tags/en/<name>/` URLs silently 302-redirect to the homepage** (chain: `/tags/<name>/` → `/tags/` → `/`). The crawler reports success but you get the homepage, not the tag page. Do NOT use tag URLs for Steam data — use the JSON APIs instead:
  - `https://store.steampowered.com/api/storesearch/?term=<query>&cc=IN&l=en` → appid + name + prices (note: `discount_percent` is always 0 here; compare `final` vs `initial` to detect real sales)
  - `https://store.steampowered.com/api/appdetails?appids=<id>&cc=IN&l=en` → authoritative `price_overview.discount_percent`, genres, release date, short_description
  - Steam search HTML endpoints (`/search/?tags=X`, `/search/results/`) IGNORE the `tags=` param silently — returns the whole catalog.
  - Steam store **app pages crawl fine** with crawl4ai (2-3s each) and contain `**Storage:** N GB` in the System Requirements section — the reliable way to get file sizes. Grep for `Storage:` (with the `**` bold markers, not `storage: `).
- **SteamDB (steamdb.info) is hard-blocked**: Cloudflare JS challenge for crawl4ai, and the shared browser IP gets *banned* ("You have been banned on SteamDB"). Don't bother — use Steam's own APIs.
- **itch.io tag pages work great** (e.g. `/games/tag-india`) — clean markdown with full genre/price filter sidebar.
- The skill is visible in the available-skills list at session start and loaded on-demand when relevant. To pre-load it into every session's context, set `HERMES_BUNDLED_SKILLS=local-web-crawler` in `~/.hermes/.env` — requires user approval since `.env` holds secrets.
- Some JS-heavy sites (SPAs, heavy React) may not render fully before timeout. Increase `--timeout` or use `--no-headless` to debug.
- Bot detection is possible on aggressive sites. crawl4ai includes `playwright-stealth` (loaded by default) to help.
- Large crawls (100+ pages) benefit from batch configs — see crawl4ai's `CrawlRunConfig` with `max_pages` and `same_domain`.
- `research.py fetch` does NOT support deep crawling — it only does single-page fetches. Use `research.py research "query"` for multi-page loops, or the Python API directly with `BFSDeepCrawlStrategy` for custom deep crawls.
- `research.py fetch` writes to stdout by default — pipe to file or redirect for large output (or use `-o <file>`).
