---
name: conference-paper-discovery
description: Find, verify, and cite accepted papers on a topic at ML conferences (NeurIPS, ICML, ICLR) by crawling the OpenReview API — search, paginate, filter accepted-only, score by keywords, verify abstracts, resolve arXiv IDs. Use for "find papers on X at conference Y", "crawl for papers on subject S", or "what did NeurIPS publish on MoE/graphics/RL?" requests.
---

# Conference Paper Discovery (OpenReview API)

OpenReview API v2 is the authoritative ground truth for "papers on topic X at conference Y" (NeurIPS/ICML/ICLR all live there). It exposes accepted/rejected status, full abstracts, and forum links — verifiable, unlike web-search snippets. Use it as the PRIMARY source for conference paper hunts; treat web sweeps (research.py, web_search) as supplementary corroboration.

## Workflow

1. **Pick the OpenReview group**: `NeurIPS.cc/2025/Conference`, `ICLR.cc/2026/Conference`, `ICML.cc/2025/Conference`, etc. Accepted papers have `content.venueid.value == group`; rejected ones carry a `Rejected_Submission` suffix venueid.
2. **Title-level search for the core term** — `GET https://api2.openreview.net/notes/search?term=<t>&group=<g>&content=title&limit=100` (paginable with `offset`). Reliable: catches nearly every paper with the term in its title (e.g. "expert" catches ~all MoE papers).
3. **Content-level sweep** with `content=all` + offset pagination. Pitfall: search is relevance-ranked and effectively capped — the reported `count` (e.g. 1689) far exceeds the unique notes you'll actually get back (~600). Cover the gap with several overlapping term searches; dedupe by `forum` id.
4. **Targeted multi-term combos** — two-word queries (`"diffusion expert"`, `"3d expert"`, `"render expert"`, `"gaussian expert"`) return union-ish related results and surface papers whose abstracts never mention the core term. Also search acronym AND expansion (e.g. both `MoE` and `mixture of experts`).
5. **Filter accepted-only**: keep notes where `content.venueid.value == group`. Searches return rejected submissions and comment/rebuttal notes (which share the paper's `forum` id — dedupe on `forum`).
6. **Score + triage**: weighted keyword scoring over title+abstract (weight per keyword: specific terms 5–6, generic terms 2). Expect false positives — the score is a triage heuristic, never proof. Verify every candidate by exact-title search and READ the abstract (≥300 chars) before reporting it on-topic.
7. **Resolve arXiv IDs**: `http://export.arxiv.org/api/query?search_query=ti:"<exact title>"&max_results=2`, parse `<id>http://arxiv.org/abs/(.+?)</id>`. Some accepted papers have no arXiv version — the OpenReview forum link stays canonical (see HMVLM case in references).
8. **Deliver with negative results**: table of confirmed papers (title, one-line what-it-is, OpenReview forum + arXiv links) PLUS an explicit "what the crawl ruled out / near-misses" section. This user expects proof of exhaustive checking — documenting excluded lookalikes (title says X, isn't X) is part of the deliverable.

## Pitfalls

- `GET /notes?group=...` (bulk list) → **403 ChallengeRequiredError** ("Challenge verification required") — bot protection, not bypassable headlessly. Use `/notes/search` instead; it works without auth. API v1 (`api.openreview.net`) is also 403-blocked.
- Rapid-fire requests → **429 Too Many Requests**. Sleep 1.2–2s between calls; after a burst, back off ~30s before resuming.
- Don't trust search `count` — dedupe by `forum` and expect far fewer unique notes.
- Keyword false-positive traps observed: "character"/"dance" in RL/NLP/medical abstracts, "mesh" in scientific ML, "lighting" in geometry papers, "expert" in title ≠ MoE (see references for the annotated hunt).
- `notes/search` requires a browser-ish User-Agent header; the default python urllib UA may be blocked.

## Companion: web-wide sweep

While the OpenReview crawl runs, launch the local NPU research loop in the background for blog/workshop/arXiv corroboration (it reports on completion):

```bash
python3 ~/.hermes/scripts/research.py research "<question>" --max-rounds 3 --pages-per-round 6 --max-pages 18
```

OpenReview output is authoritative; fold the web sweep in only if it adds verified items.

## Support files

- `scripts/openreview_crawl.py` — re-runnable crawler: `--group`, repeatable `--term`, keyword weights, accepted-only filter, min-score, optional arXiv resolution. Edit TERMS/KEYWORDS per hunt.
- `references/openreview-api-notes.md` — verified API endpoints, response shapes, rate-limit behavior, and the annotated NeurIPS MoE×graphics hunt (exact queries, what worked, false positives, final paper list with arXiv IDs).
