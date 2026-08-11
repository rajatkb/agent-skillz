# OpenReview API notes (verified Aug 2026)

## Endpoints (API v2, no auth)

| Endpoint | Status | Notes |
|---|---|---|
| `GET https://api2.openreview.net/notes/search?term=X&group=G&content=all&limit=100&offset=N` | ✅ works | Relevance-ranked. `content` ∈ {all, title, abstract}. Requires browser-ish User-Agent. |
| `GET https://api2.openreview.net/notes?group=G&limit=1000` | ❌ 403 | `{"name":"ChallengeRequiredError","message":"Challenge verification required (…)"}` — bot protection, not bypassable headlessly. |
| `GET https://api.openreview.net/notes?group=G` (v1) | ❌ 403 | Also blocked. |

Response shape (v2 notes): `content.title.value`, `content.abstract.value`, `content.venueid.value`, `forum` (stable paper id — use for dedupe and links), `id`.

## Group / venueid semantics

- Accepted papers: `venueid == group` (e.g. `NeurIPS.cc/2025/Conference`).
- Rejected submissions: `NeurIPS.cc/2025/Conference/Rejected_Submission`.
- Comment/rebuttal/decision notes share the paper's `forum` id — always dedupe on `forum`.
- Other conferences: `ICLR.cc/<year>/Conference`, `ICML.cc/<year>/Conference`.

## Search behavior quirks

- `term=expert&content=all` reported `count: 1689` but offset pagination 0–1600 deduped to only ~594 unique notes. The search is relevance-capped; overlapping terms are required for full coverage.
- `content=title` returns few, precise hits (69 for "expert") — good first pass.
- Multi-term queries (`"gaussian expert"`, `"diffusion expert"`) behave like related-content unions — good for surfacing papers that never say the core term.
- Rate limit: 429 after ~10–15 rapid requests; recover with ~30s cooldown. Keep ≥1.2s sleeps.

## Annotated hunt: MoE × computer graphics at NeurIPS 2024–2025

Goal: recent NeurIPS papers applying Mixture of Experts to graphics (rendering, 3D, NeRF/3DGS, image/video synthesis, avatars, motion).

What worked, in order:
1. Title search `expert` (69 papers) → 11 graphics-scored, mostly false positives.
2. Full `content=all` crawl of `expert` + `mixture of experts` (694 unique, 275 accepted) → still mostly keyword false positives ("character" in RL/medical abstracts, "dance" in text-to-video, "mesh" in scientific ML).
3. Targeted combos found the real papers: `diffusion expert` → ALTER; `motion expert` → HMVLM; `3d expert`/`mixture`-title → MEGADance; `diffusion expert` (2024) → Remix-DiT; `mixture of experts` (2024) → Neural Experts, MoLE.
4. Every candidate verified by exact-title search → read abstract → checked `venueid == group`.

Confirmed papers (final deliverable):
- **ALTER: All-in-One Layer Pruning and Temporal Expert Routing for Efficient Diffusion Generation** — NeurIPS 2025 — openreview.net/forum?id=021PIPyOU1 — arXiv:2505.21817
- **MEGADance: MoE Architecture for Genre-Aware 3D Dance Generation** — NeurIPS 2025 — openreview.net/forum?id=oIBwHvF930 — arXiv:2505.17543
- **HMVLM: Human Motion-Vision-Language Model via MoE LoRA** — NeurIPS 2025 — openreview.net/forum?id=Gvq2AfuVEA — NO arXiv version (OpenReview is canonical)
- **Neural Experts: MoE for Implicit Neural Representations** — NeurIPS 2024 — openreview.net/forum?id=wWguwYhpAY — arXiv:2410.21643
- **MoLE: Human-centric Text-to-image Diffusion via Mixture of Low-rank Experts** — NeurIPS 2024 — openreview.net/forum?id=XWzw2dsjWd — arXiv:2410.23332
- **Remix-DiT: Mixing Diffusion Transformers for Multi-Expert Denoising** — NeurIPS 2024 — openreview.net/forum?id=vo5LONGAdo — arXiv:2412.05628

Negative results (documented to prove exhaustive checking):
- No NeurIPS 2025 paper combines MoE with NeRF/3DGS/mesh rendering. Swept the full splatting paper list (IBGS, TreeSplat, HoliGS, BecomingLit, DEGauss, ~30 papers) — none use expert routing.
- False-positive traps: "expert" in title ≠ MoE (PocketSR = lightweight diffusion SR; LayerCraft/WISA = LLM-agent orchestration; Doctor Approved, Dimension-Reduction Attack = "experts" in the colloquial sense). MoE acronym in title ≠ graphics (MoME = audio-visual speech recognition; CryptoMoE = private LLM inference; FlashMoE = distributed training).

## arXiv ID resolution

`http://export.arxiv.org/api/query?search_query=ti:"<exact title>"&max_results=2` → parse `<id>http://arxiv.org/abs/([\w.\-/]+)</id>`. Sleep ~3s between queries (rate-sensitive). Some accepted conference papers never appear on arXiv.
