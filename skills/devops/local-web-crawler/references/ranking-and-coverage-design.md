# Research Loop: BM25 + DDGS Deterministic Ranking, Gemma Steering, Coverage Gate

Status: **ranking architecture IMPLEMENTED and live in research.py (Aug 2026)**, including content-preview ranking (rank on actual page text), re-rank-on-fetch (fetched pages get real-content BM25), and re-search triggers (DDGS is a recurring engine, not a one-shot seed — `SEARCH_FLOOR` / `MIN_DOMAINS` / `MAX_SEARCHES` + `gap_query()`). The coverage gate (`should_stop`) is still a planned fix — the loop stops on budget.

## Why (user's correction, verbatim intent)

- "Use the ddgs ranking" — DDGS position IS a signal (corrects the earlier "DDGS has no opinion" draft). DDGS rank breaks BM25 ties.
- "Content specific bm25 reverse index strategy" — score candidates by BM25 against query terms over their content.
- "Only after we have filtered through all of them does Gemma take hold... looks at the top 10 items and judges the next step."
- "Instead of constantly asking gemma to rank. gemma is good extractor and summarizer but it should not be ranking more than 10 items at a time."
- "10 is subjective and deepseek/hermes agent can take a call on that when calling the script" → `--gemma-rank-top` CLI arg, default 10.

## Implemented ranking (live in research.py)

### Frontier seeding — `rank_candidates(candidates, query)`

```
final_score = BM25_WEIGHT(0.6) · bm25_norm + (1−0.6) · ddgs_positional
ddgs_positional = 1 / (ddgs_rank + 2)      # rank 1 → 0.333, rank 8 → 0.100
bm25_norm = raw_bm25 / max(raw_bm25 in pool)
```

- `ddgs_search()` now returns `ddgs_rank` (1-indexed position) per result.
- Every frontier entry carries provenance: `reason="bm25=0.84 ddgs=0.3333"`.
- All search hits across sub-queries are pooled, scored together, deduped, then seeded.

### In-page link scoring — `score_discovered_links(links, query, parent_score)`

```
final = (1 − PARENT_WEIGHT(0.3)) · bm25_norm(anchor+title+context) + 0.3 · min(parent_score, 1)
```

- Gemma's `extract_links()` (renamed from `rank_links`) returns `{url, title, anchor, context}` with NO scores — RANK_SYSTEM prompt explicitly says "Do NOT score links — extraction only."
- BM25 corpus for a link = anchor text + title + surrounding sentence.

### Steering — `steer_frontier(query, items, model, max_items)`

Once per round, on the top `--gemma-rank-top` (default 10) unvisited frontier items:

```
STEER_SYSTEM: "Decide the next action for EACH link... visit|priority|skip.
priority = fetch next round (very relevant), visit = keep in queue, skip = drop it."
```

Applied: `priority` → score +1.5, `skip` → removed from frontier, `visit` → unchanged.
Observed live: "steered top 10: 2 priority, 2 skipped, 5 kept" per round.

### BM25 core (`BM25Index`)

```python
k1 = 1.5, b = 0.75
score(url, q) = Σ over query terms t:
    IDF(t) · (tf(t,url)·(k1+1)) / (tf(t,url) + k1·(1 − b + b·dl/avgdl))
IDF(t) = ln((N − df(t) + 0.5) / (df(t) + 0.5) + 1)
```

- Tokenize: lowercase, strip punctuation, drop stopwords + tokens ≤2 chars (reuses STOPWORDS from `prune_relevant`).
- Reverse index: term → postings {url: term_freq}; df(t) = # docs containing t.
- Tunables: `BM25_K1`, `BM25_B`, `BM25_WEIGHT` (0.6), `PARENT_WEIGHT` (0.3) env vars.

## Gemma's limited roles (final)

1. Refine query (round 0, temp 0.5)
2. Extract facts (FACT_SYSTEM) + numbers (NUMBER_SYSTEM) — quote-anchored
3. Extract links from a page — `{url, title, anchor, context}`, no scores
4. Steer top-10 once per round — visit|priority|skip

Gemma never sees the whole frontier, never scores >10 items, never emits numeric ranks for the pool.

### Content-preview ranking — `content_preview()` + `rank_with_content()` (Aug 2026)

User correction: "the content should be ranked not some title or metadata." Search hits are no longer BM25-scored on title+snippet only:

- Round 0 (and every re-search): each candidate's **head content is fetched via lean HTTP** (`content_preview()`, capped `CONTENT_PREVIEW_CHARS=20000`, no browser), then `rank_with_content()` BM25-indexes the ACTUAL text. Unfetchable pages (JS walls) fall back to title+snippet — flagged `content_scored=False`.
- Observed live: 19/22 candidates content-scored in one run; a page with a generic title but content matching the query correctly outranked one with a great title but no content match.

### Re-rank on fetch — real-content provenance

After a successful fetch, the frontier entry's score is replaced with BM25 over the **pruned real content** (`content_bm25=` appended to `reason`). Provenance reflects what the page actually said, not what DDGS claimed. Note the score scale differs from the seeding blend (raw BM25 vs 0-1 normalized) — fine, both are deterministic and order-comparable within the frontier.

### Re-search triggers — DDGS as a recurring engine (Aug 2026)

User correction: "DDGS is never invoked again... should it not be if Gemma decides we are off track, or to increase diversity?"

- Checked at each round start: `best unvisited frontier score < SEARCH_FLOOR (0.20)` OR `distinct domains in 03_notes/ < MIN_DOMAINS (3)`, AND `searches < MAX_SEARCHES (4)`.
- Trigger path: `gap_query()` — Gemma writes ONE follow-up query given the covered domains (the only LLM step; deterministic triggers, Gemma only authors the query) → `ddgs_search()` → content-preview → BM25 rank → merge into frontier (deduped vs visited + existing frontier).
- Search count persisted in `session.json["searches"]` (init 1 at round 0, incremented per trigger). Resume-safe.
- Observed live: fired twice in one run — first +6 new candidates, second +0 (all already seen, dedup holding). Log line: `[research] frontier weak (best=0.66, domains=0/3) — re-searching: '...'`.

## Coverage gate (`should_stop`) — planned, NOT implemented

Observed failure (live run, Aug 2026): query "best local LLM for coding assistant Windows laptop" stopped at `--max-pages 4` with **37 frontier links unvisited, including 3 at score 9 and 3 at 8**, only 2 distinct domains read (huggingface.co, apidog.com), while deepseek.com / ollama.com / vellum.ai sat ignored in the frontier. findings.md even listed open questions answerable from the ignored sources. The loop has NO coverage notion — only `frontier empty` or `pages_fetched >= max_pages`.

Stop only when ALL hold (checked after each round):

1. **Frontier exhausted by quality**: best unvisited frontier score < 7.0 (or frontier empty).
2. **Source diversity**: distinct domains represented in `03_notes/` ≥ 4.
3. **Saturation**: new facts this round / total facts < 0.15 (facts = count of `- **` bullets in notes; track delta vs prior round).
4. **Open-questions closure**: any open question in a preliminary synthesis that IS answerable from remaining frontier → continue.

`--max-pages` / `--max-rounds` become hard safety ceilings, not the primary stop.

## What the ranking redesign fixed (measured)

- Old: search hits flat 7.0; Gemma scored links 0-10 per page (subjective, no rubric, no recalibration — a 9 on a Medium post outranked an 8 from vendor docs).
- New (live run, same query): frontier seeds with visible `bm25=/ddgs=` provenance; 4 pages from 4 different domains (huggingface, ai-ollama, onyx, promptquorum) vs old 2-domain echo; steering measurably re-ranked the frontier (5 priorities, 4 skips); prompt tokens 16.5K for 4 pages vs 22.4K old (and 98K pre-pruning on one page).

## CLI surface (implemented)

```
--gemma-rank-top 10     # items Gemma steers per round; DeepSeek/Hermes chooses per call
--pages-per-round 2     # fetch batch
--max-rounds 5          # hard ceiling
--max-pages 30          # safety cap (not the primary stop, until coverage gate lands)
```
