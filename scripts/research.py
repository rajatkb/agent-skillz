#!/usr/bin/env python3
"""research.py — unified crawl4ai tool: one-shot fetch OR autonomous Gemma research loop.

Lives at ~/.hermes/scripts/research.py. Requires: crawl4ai, ddgs, FLM NPU server (gemma4-it:e2b default).

Modes:
  fetch    — one-shot page fetch → clean markdown (no Gemma, no loop). Replaces old crawl.py.
  research — deep loop: Gemma refines → DDGS searches → crawl4ai fetches → Gemma summarizes/ranks
             → repeat → synthesis. Writes a session tree for DeepSeek to consume.

Usage:
  python3 research.py fetch https://example.com https://a.com -o out.md [--no-prune] [--bm25 --query "terms"] [--verbose] [--no-headless] [--timeout 60]
  python3 research.py research "question" [--model gemma4-it:e2b] [--max-rounds 5] [--pages-per-round 6] [--max-pages 30] [--out-dir ~/.hermes/crawl_sessions] [--no-refine] [--verbose]

Research session tree:
  <out-dir>/<slug>/
    session.json   state (resumable)
    00_plan.md     refined queries + strategy
    01_search/     DDGS results per sub-query
    02_pages/      raw crawled markdown (reference)
    03_notes/      ★ Gemma-compressed notes per page (DeepSeek-readable layer)
    04_links/      frontier: scored next links per round
    05_synthesis/  final findings.md
    tree.md        auto-generated index
"""

import argparse
import asyncio
import gzip
import io
import json
import math
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

# ── config (never hardcoded) ────────────────────────────────────────────────
FLM_BASE_URL = os.environ.get("FLM_BASE_URL", "http://127.0.0.1:50001/v1")
MODEL = os.environ.get("FLM_MODEL", "gemma4-it:e2b")
DDGS_DELAY = float(os.environ.get("DDGS_DELAY", "1.5"))
CHUNK_CHARS = int(os.environ.get("GEMMA_CHUNK_CHARS", "24000"))  # ~6k tokens
CHUNK_OVERLAP = 1500
MAX_PAGE_EXTRACT_CHARS = int(os.environ.get("MAX_PAGE_EXTRACT_CHARS", "25000"))  # cap per-page extraction cost


# ── lean HTTP fetch layer (no browser!) ─────────────────────────────────────
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
JS_SHELL_MARKERS = ("id=\"root\"", "id=\"app\"", "id=\"__next\"", "__NUXT__",
                    "window.__INITIAL", "ng-app", "v-cloak", "react-root")
MIN_HTML_LEN = 300


def http_fetch(url: str, timeout: int = 30) -> dict:
    """Plain-HTTP page fetch (no Chromium): returns {ok, content, via, error}.

    content = markdown-ish text extracted from HTML via bs4. ~few MB RAM vs
    400-600MB for a headless Chromium instance. 'via' = 'http' or 'browser'.
    """
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read(5_000_000)  # cap at 5MB — never OOM the 3.8GB box
            enc = r.headers.get("Content-Encoding", "")
            ctype = r.headers.get("Content-Type", "")
        if "gzip" in enc:
            raw = gzip.decompress(raw)
        if "html" not in ctype and "text/plain" not in ctype and "xml" not in ctype:
            return {"ok": False, "content": f"not HTML ({ctype})", "via": "http",
                    "error": f"content-type {ctype}"}
        html = raw.decode("utf-8", errors="replace")
        text = html_to_markdown(html)
        if len(text) < MIN_HTML_LEN:
            # Only a JS shell if the raw HTML actually has SPA markers —
            # tiny-but-real pages (like example.com) must NOT trigger the browser.
            if any(m in html for m in JS_SHELL_MARKERS):
                return {"ok": False, "content": text, "via": "http",
                        "error": "too short / JS shell — needs browser"}
        return {"ok": True, "content": text, "via": "http", "error": None}
    except Exception as e:
        return {"ok": False, "content": "", "via": "http", "error": str(e)}


def html_to_markdown(html: str) -> str:
    """Extract readable markdown-ish text from HTML using bs4 (no browser)."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header",
                     "aside", "form", "iframe", "svg", "button", "select"]):
        tag.decompose()
    # headings → markdown
    for h in soup.find_all(re.compile(r"^h[1-6]$")):
        level = int(h.name[1])
        h.insert_before("\n" + "#" * level + " " + h.get_text(" ", strip=True) + "\n")
        h.unwrap()
    # paragraphs / list items → lines
    for p in soup.find_all(["p", "li", "blockquote", "pre"]):
        txt = p.get_text(" ", strip=True)
        if txt:
            p.insert_before(txt + "\n")
        p.decompose()
    text = soup.get_text("\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def looks_like_js_shell(http_result: dict) -> bool:
    return not http_result.get("ok") and "JS shell" in (http_result.get("error") or "")


async def browser_fetch(urls: list, max_concurrent: int = 2, verbose: bool = False,
                        no_prune: bool = False, bm25_query: str = None) -> dict:
    """crawl4ai browser fallback — used ONLY when plain HTTP can't get the page.
    Runs in memory-saving mode; low concurrency to keep RAM lean."""
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
    from crawl4ai.content_filter_strategy import PruningContentFilter, BM25ContentFilter

    browser = BrowserConfig(
        headless=True,
        verbose=verbose,
        light_mode=True,               # lean rendering
        text_mode=True,                # skip heavy layout/painting
        viewport_width=1024, viewport_height=768,
        extra_args=[
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-extensions",
            "--disable-software-rasterizer",
        ],
    )
    cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        word_count_threshold=1 if no_prune else 10,
        verbose=verbose,
        semaphore_count=max_concurrent,   # limit concurrent page loads
        page_timeout=30000,
    )
    if not no_prune:
        if bm25_query:
            cfg.content_filter = BM25ContentFilter(user_query=bm25_query, bm25_threshold=1.0)
        else:
            cfg.content_filter = PruningContentFilter(threshold=0.45, threshold_type="dynamic")

    out = {}
    async with AsyncWebCrawler(config=browser) as crawler:
        async def one(url: str):
            try:
                res = await crawler.arun(url=url, config=cfg)
                return url, (res.success, res.markdown if res.success else res.error_message)
            except Exception as e:
                return url, (False, str(e))
        results = await asyncio.gather(*[one(u) for u in urls])
    for url, (ok, content) in results:
        out[url] = {"ok": ok, "content": content, "via": "browser", "error": None if ok else str(content)[:200]}
    return out


async def fetch_pages(urls: list, max_concurrent: int = 2, verbose: bool = False,
                      no_prune: bool = False, bm25_query: str = None) -> dict:
    """Hybrid fetch: plain HTTP first (lean), browser fallback for JS-heavy/failed pages."""
    out = {}
    http_results = {}
    need_browser = []

    # Phase 1: plain HTTP for all URLs — no Chromium spawned for these
    for u in urls:
        r = http_fetch(u)
        http_results[u] = r
        if r["ok"]:
            out[u] = r
        else:
            need_browser.append(u)

    # Phase 2: browser only for the stragglers
    if need_browser:
        if verbose:
            print(f"  [http→browser] {len(need_browser)} pages need JS rendering")
        browser_results = await browser_fetch(need_browser, max_concurrent=max_concurrent,
                                              verbose=verbose, no_prune=no_prune, bm25_query=bm25_query)
        for u, r in browser_results.items():
            if r["ok"]:
                out[u] = r
            else:
                out[u] = {"ok": False, "content": http_results[u].get("content", ""),
                          "via": "http+browser", "error": r.get("error") or http_results[u].get("error")}
    return out


def cmd_fetch(args) -> int:
    """One-shot fetch: URLs → clean markdown (old crawl.py behavior)."""
    fetched = asyncio.run(fetch_pages(
        args.urls, verbose=args.verbose, no_prune=args.no_prune, bm25_query=args.query,
    ))
    outputs = {}
    for url, res in fetched.items():
        if not res["ok"]:
            print(f"FAILED: {url} — {res['content']}", file=sys.stderr)
            continue
        outputs[url] = f"# Source: {url}\n\n{res['content']}"

    if not outputs:
        sys.exit(1)

    full = "\n\n---\n\n".join(outputs.values())
    if args.output:
        out_path = Path(args.output)
        if not out_path.suffix:
            out_path = out_path.with_suffix(".md")
        out_path.write_text(full)
        print(f"Written to {out_path}")
    else:
        print(full)
    return 0


# ── Gemma client (FLM, OpenAI-compatible) with usage telemetry ─────────────
class Stats:
    """Per-run telemetry: tokens consumed, wall time, measured tok/s from FLM."""

    def __init__(self):
        self.calls = []  # {stage, model, prompt_tokens, completion_tokens, elapsed, tps}
        self.start = time.time()

    def add(self, stage, model, prompt_tokens, completion_tokens, elapsed, tps):
        self.calls.append({"stage": stage, "model": model,
                           "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
                           "elapsed": elapsed, "tps": tps})

    @property
    def total_prompt_tokens(self):
        return sum(c["prompt_tokens"] for c in self.calls)

    @property
    def total_completion_tokens(self):
        return sum(c["completion_tokens"] for c in self.calls)

    @property
    def total_tokens(self):
        return self.total_prompt_tokens + self.total_completion_tokens

    @property
    def wall_time(self):
        return time.time() - self.start

    def avg_tps(self):
        """Weighted average decode speed: total completion tokens / total decode time."""
        toks = sum(c["completion_tokens"] for c in self.calls if c["tps"])
        time_s = sum(c["completion_tokens"] / c["tps"] for c in self.calls if c["tps"])
        return (toks / time_s) if time_s else 0.0

    def report(self) -> str:
        lines = [
            "# Run telemetry", "",
            f"- model: {self.calls[0]['model'] if self.calls else 'n/a'}",
            f"- gemma calls: {len(self.calls)}",
            f"- prompt tokens: {self.total_prompt_tokens:,}",
            f"- completion tokens: {self.total_completion_tokens:,}",
            f"- total tokens: {self.total_tokens:,}",
            f"- wall time: {self.wall_time:.1f}s",
            f"- avg decoding speed: {self.avg_tps():.1f} tok/s (measured by FLM)",
            "",
            "| stage | calls | prompt tok | completion tok | wall s |",
            "| --- | --- | --- | --- | --- |",
        ]
        by_stage = {}
        for c in self.calls:
            by_stage.setdefault(c["stage"], []).append(c)
        for stage, cs in sorted(by_stage.items()):
            lines.append(f"| {stage} | {len(cs)} | {sum(c['prompt_tokens'] for c in cs):,} "
                         f"| {sum(c['completion_tokens'] for c in cs):,} "
                         f"| {sum(c['elapsed'] for c in cs):.1f} |")
        return "\n".join(lines)


STATS = Stats()


def gemma_chat(system: str, user: str, model: str = MODEL, max_tokens: int = 1200,
               temperature: float = 0.1, timeout: int = 180, stage: str = "general") -> str:
    t0 = time.time()
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    req = urllib.request.Request(
        FLM_BASE_URL + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    elapsed = time.time() - t0
    usage = data.get("usage", {})
    decoding_s = usage.get("decoding_duration", 0) or 0
    comp_tokens = usage.get("completion_tokens", 0) or 0
    tps = (comp_tokens / decoding_s) if decoding_s and comp_tokens else 0.0
    STATS.add(stage, model, usage.get("prompt_tokens", 0) or 0, comp_tokens, elapsed, tps)
    return data["choices"][0]["message"]["content"].strip()


def gemma_chat_retry(system: str, user: str, **kw) -> str:
    """Retry with fail-fast on timeout: a wedged FLM won't recover within retries,
    so a socket timeout aborts immediately instead of burning 3×timeout seconds."""
    last_err = None
    for attempt in range(3):
        try:
            return gemma_chat(system, user, **kw)
        except Exception as e:
            last_err = e
            if isinstance(e, (TimeoutError, socket.timeout, urllib.error.URLError)) and "timed out" in str(e).lower():
                raise RuntimeError(f"FLM unresponsive (timeout) — server likely wedged: {e}")
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"gemma_chat failed after 3 attempts: {last_err}")


def flm_alive() -> bool:
    """Cheap liveness probe: is FLM actually serving? 3s cap."""
    try:
        with urllib.request.urlopen(FLM_BASE_URL + "/models", timeout=3):
            return True
    except Exception:
        return False


def extract_json(text: str):
    """Pull JSON out of a Gemma response (handles code fences / prose / truncation)."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\[.*?\]|\{.*?\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    else:
        m = re.search(r"(\[.*\]|\{.*\})", text, re.S)
        if m:
            text = m.group(1)
    text = text.strip()
    # tolerate truncated output: strip trailing comma, close dangling arrays/objects
    if not text.endswith(("]", "}")):
        text = re.sub(r",\s*$", "", text)
        if text.count("[") > text.count("]"):
            text += "]"
        elif text.count("{") > text.count("}"):
            text += "}"
    return json.loads(text)


def chunk_text(text: str, chunk_chars: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP):
    """Split long text into overlapping chunks for Gemma's context window."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    if len(text) <= chunk_chars:
        return [text]
    chunks, start = [], 0
    while start < len(text):
        end = min(start + chunk_chars, len(text))
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks


# ── DDGS search layer ───────────────────────────────────────────────────────
# Domains that plain HTTP + headless Chromium cannot meaningfully fetch
# (video walls, hard anti-bot, login-required). Filtered from search results.
BLOCKED_DOMAINS = ("youtube.com", "youtu.be", "reddit.com", "old.reddit.com",
                   "twitter.com", "x.com", "facebook.com", "instagram.com",
                   "tiktok.com", "twitch.tv", "discord.com", "linkedin.com")


def is_blocked_domain(url: str) -> bool:
    try:
        host = urllib.parse.urlsplit(url).netloc.lower()
    except Exception:
        return True
    return any(host == d or host.endswith("." + d) for d in BLOCKED_DOMAINS)


def ddgs_search(query: str, max_results: int = 8) -> list:
    from ddgs import DDGS  # new package name; old duckduckgo_search is renamed + broken backend
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results, backend="auto"))
    except Exception:
        # fallback: bing backend via ddgs
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results, backend="bing"))
    out = []
    for r in results:
        href = r.get("href") or r.get("url")
        if not href or is_blocked_domain(href):
            continue
        out.append({
            "url": href,
            "title": r.get("title", "").strip(),
            "snippet": r.get("body", "").strip(),
            "ddgs_rank": len(out) + 1,   # positional prior — DDGS order matters
        })
    return out


# ── BM25 deterministic ranker (reverse index — no LLM in this path) ─────────
BM25_K1 = float(os.environ.get("BM25_K1", "1.5"))
BM25_B = float(os.environ.get("BM25_B", "0.75"))
BM25_WEIGHT = float(os.environ.get("BM25_WEIGHT", "0.6"))   # vs DDGS rank
PARENT_WEIGHT = float(os.environ.get("PARENT_WEIGHT", "0.3"))  # provenance prior for discovered links
CONTENT_PREVIEW_CHARS = int(os.environ.get("CONTENT_PREVIEW_CHARS", "20000"))  # head-content cap for ranking
SEARCH_FLOOR = float(os.environ.get("SEARCH_FLOOR", "0.20"))   # re-search when best frontier score < this
MIN_DOMAINS = int(os.environ.get("MIN_DOMAINS", "3"))          # diversity floor before re-search
MAX_SEARCHES = int(os.environ.get("MAX_SEARCHES", "4"))        # hard cap on total DDGS rounds


def tokenize(text: str) -> list:
    return [w for w in re.findall(r"[a-z0-9][a-z0-9+-]{1,}", text.lower())
            if w not in STOPWORDS and len(w) > 2]


class BM25Index:
    """Reverse index: term → postings {doc_id: tf}. Classic BM25 (k1=1.5, b=0.75)."""

    def __init__(self, k1: float = BM25_K1, b: float = BM25_B):
        self.k1, self.b = k1, b
        self.doc_count = 0
        self.doc_len = {}     # doc_id → term count
        self.postings = {}    # term → {doc_id: tf}
        self.avgdl = 0.0

    def add(self, doc_id: str, text: str):
        terms = tokenize(text)
        if not terms:
            return
        self.doc_len[doc_id] = len(terms)
        tf = {}
        for t in terms:
            tf[t] = tf.get(t, 0) + 1
        for t, c in tf.items():
            self.postings.setdefault(t, {})[doc_id] = c
        self.doc_count += 1
        self.avgdl = sum(self.doc_len.values()) / self.doc_count

    def idf(self, term: str) -> float:
        df = len(self.postings.get(term, {}))
        return math.log((self.doc_count - df + 0.5) / (df + 0.5) + 1.0)

    def score(self, doc_id: str, query: str) -> float:
        dl = self.doc_len.get(doc_id, 0)
        if dl == 0 or not self.doc_count:
            return 0.0
        s = 0.0
        for t in tokenize(query):
            tf = self.postings.get(t, {}).get(doc_id, 0)
            if tf == 0:
                continue
            idf = self.idf(t)
            denom = tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
            s += idf * (tf * (self.k1 + 1)) / denom
        return s


def rank_candidates(candidates: list, query: str, bm25_weight: float = BM25_WEIGHT) -> list:
    """Score + sort search candidates deterministically.
    final = bm25_weight·bm25_norm + (1−bm25_weight)·ddgs_positional.
    Mutates entries with 'bm25', 'ddgs_score', 'final_score'; returns sorted list."""
    idx = BM25Index()
    for c in candidates:
        idx.add(c["url"], f"{c.get('title', '')} {c.get('snippet', '')}")
    raw = {c["url"]: idx.score(c["url"], query) for c in candidates}
    mx = max(raw.values()) if raw else 1.0
    for c in candidates:
        bm = raw[c["url"]] / mx if mx else 0.0
        dd = 1.0 / (c.get("ddgs_rank", 1) + 2)          # rank 1 → .33, rank 8 → .10
        c["bm25"] = round(bm, 4)
        c["ddgs_score"] = round(dd, 4)
        c["final_score"] = round(bm25_weight * bm + (1 - bm25_weight) * dd, 4)
    candidates.sort(key=lambda c: -c["final_score"])
    return candidates


def score_discovered_links(links: list, query: str, parent_score: float,
                           parent_weight: float = PARENT_WEIGHT) -> list:
    """Deterministic scoring for links Gemma extracted from a page.
    final = (1−pw)·bm25_norm(anchor+title) + pw·min(parent_score,1)."""
    idx = BM25Index()
    for l in links:
        ctx = f"{l.get('title', '')} {l.get('anchor', '')} {l.get('context', '')}"
        idx.add(l["url"], ctx)
    raw = {l["url"]: idx.score(l["url"], query) for l in links}
    mx = max(raw.values()) if raw else 1.0
    for l in links:
        bm = raw[l["url"]] / mx if mx else 0.0
        l["bm25"] = round(bm, 4)
        l["final_score"] = round((1 - parent_weight) * bm + parent_weight * min(parent_score, 1.0), 4)
    links.sort(key=lambda l: -l["final_score"])
    return links


def content_preview(url: str, timeout: int = 20) -> str:
    """Fetch a page's head content (capped) for RANKING — lean HTTP, no browser.
    Returns '' on failure so callers fall back to title+snippet scoring."""
    try:
        r = http_fetch(url, timeout=timeout)
        if r["ok"]:
            return r["content"][:CONTENT_PREVIEW_CHARS]
    except Exception:
        pass
    return ""


def rank_with_content(candidates: list, query: str, bm25_weight: float = BM25_WEIGHT) -> list:
    """Score candidates using their ACTUAL head content where fetchable;
    falls back to title+snippet for unfetchable pages. Adds 'content_scored' flag."""
    idx = BM25Index()
    for c in candidates:
        text = c.get("_preview") or f"{c.get('title', '')} {c.get('snippet', '')}"
        idx.add(c["url"], text)
    raw = {c["url"]: idx.score(c["url"], query) for c in candidates}
    mx = max(raw.values()) if raw else 1.0
    for c in candidates:
        bm = raw[c["url"]] / mx if mx else 0.0
        dd = 1.0 / (c.get("ddgs_rank", 1) + 2)
        c["bm25"] = round(bm, 4)
        c["ddgs_score"] = round(dd, 4)
        c["content_scored"] = bool(c.get("_preview"))
        c["final_score"] = round(bm25_weight * bm + (1 - bm25_weight) * dd, 4)
    candidates.sort(key=lambda c: -c["final_score"])
    return candidates


# ── Gemma prompts (extraction-only, quote-anchored, anti-hallucination) ─────
REFINE_SYSTEM = (
    "You are a research query planner. Given a broad research goal, produce up to 3 "
    "concrete search-engine queries that would surface the best sources. "
    "Return ONLY a JSON array of strings, no prose."
)

FACT_SYSTEM = (
    "You are a FACT EXTRACTOR. From the given page text, extract ONLY facts that are "
    "explicitly stated. For EVERY fact you must include the exact verbatim quote from the "
    "page that supports it. If a detail is not stated in the page, do NOT include it — "
    "never infer, estimate, or extrapolate. Skip navigation, ads, boilerplate. "
    'Return ONLY JSON: [{"fact": "...", "quote": "exact words from the page"}]'
)

NUMBER_SYSTEM = (
    "You are a NUMBER EXTRACTOR. From the given page text, extract every numeric claim "
    "(speeds, sizes, prices, percentages, specs) with its exact verbatim context sentence. "
    "Do NOT convert units, do NOT estimate, do NOT invent numbers. If the page has no "
    "numbers, return []. "
    'Return ONLY JSON: [{"value": "...", "unit": "...", "context": "verbatim sentence"}]'
)

RANK_SYSTEM = (
    "You are a link EXTRACTOR. Given a research query and a page's content, extract the "
    "up to 8 links most relevant to the query. ONLY use URLs that appear VERBATIM in the "
    "page content — never invent or reconstruct URLs. For each link include the anchor "
    "text and the surrounding sentence as context. Return ONLY JSON: "
    '[{"url": "...", "title": "...", "anchor": "...", "context": "surrounding sentence"}]'
    " Do NOT score links — extraction only."
)

SYNTH_SYSTEM = (
    "You are a research synthesist. Given evidence notes from multiple sources, write "
    "a findings.md: an executive summary, key findings with source attribution "
    "(markdown links), open questions, and a short 'further reading' list. "
    "STRICT RULES: (1) Every claim must trace to a quoted fact in the notes — cite the "
    "source URL next to it. (2) NEVER invent numbers, stats, names, or URLs. If a detail "
    "is not backed by a quote, do not include it. (3) If the notes contradict each other, "
    "say so explicitly. (4) If evidence is thin, state that clearly."
)

STEER_SYSTEM = (
    "You are a research triage agent. You are given up to 10 candidate links from a "
    "research frontier, each with its deterministic relevance score and a snippet. "
    "Decide the next action for EACH link. Return ONLY JSON: "
    '[{"url": "...", "action": "visit|priority|skip", "reason": "..."}] '
    '"priority" = fetch next round (very relevant), "visit" = keep in queue, '
    '"skip" = drop it (dead end, low value, duplicate topic). Be decisive — skip '
    "links that would not add new information."
)


GAP_SYSTEM = (
    "You are a research gap analyst. Given the original research query and the set of "
    "domains already covered, identify what is MISSING and produce ONE new "
    "search-engine query that would surface diverse, undiscovered sources on the gap. "
    "Return ONLY a JSON string, no prose."
)


def gap_query(query: str, covered_domains: list, model: str) -> str:
    """Gemma writes ONE follow-up query when the frontier is exhausted or
    source diversity is too low. Deterministic triggers; Gemma only writes."""
    try:
        domains = ", ".join(sorted(covered_domains)) or "none yet"
        raw = gemma_chat_retry(
            GAP_SYSTEM,
            f"Original query: {query}\n\nDomains already covered: {domains}\n\nNew search query:",
            model=model, max_tokens=150, temperature=0.5, stage="gap",
        )
        out = extract_json(raw)
        if isinstance(out, str) and out.strip():
            return out.strip()
        if isinstance(out, dict) and out.get("query"):
            return out["query"]
    except Exception:
        pass
    return query  # fallback: re-run the original


def steer_frontier(query: str, items: list, model: str, max_items: int = 10) -> list:
    """Gemma's ONLY ranking role: triage the top slice of the frontier.
    Returns list of {url, action}. Never sees more than max_items."""
    if not items:
        return []
    blob = "\n".join(
        f"- {i+1}. [{f['url']}] score={f.get('final_score', f.get('score', 0)):.2f} :: "
        f"{(f.get('snippet') or f.get('title') or '')[:150]}"
        for i, f in enumerate(items[:max_items])
    )
    try:
        raw = gemma_chat_retry(STEER_SYSTEM, f"Research query: {query}\n\nCandidates:\n{blob}",
                               model=model, max_tokens=700, temperature=0.1, stage="steer")
        out = extract_json(raw)
        if not isinstance(out, list):
            return []
        return [v for v in out if isinstance(v, dict) and v.get("url")]
    except Exception:
        return []


def refine_query(query: str, model: str) -> list:
    try:
        raw = gemma_chat_retry(REFINE_SYSTEM, f"Research goal: {query}", model=model,
                               max_tokens=300, temperature=0.5, stage="refine")
        qs = extract_json(raw)
        if isinstance(qs, str):
            qs = [qs]
        qs = [q for q in qs if isinstance(q, str) and q.strip()][:3]
        return qs or [query]
    except Exception:
        return [query]


def extract_json_list(system: str, user: str, model: str, stage: str,
                      max_tokens: int = 800) -> list:
    """Run an extraction prompt, safely return a list ([] on any failure)."""
    try:
        raw = gemma_chat_retry(system, user, model=model, max_tokens=max_tokens,
                               temperature=0.1, stage=stage)
        out = extract_json(raw)
        return out if isinstance(out, list) else []
    except Exception:
        return []


# ── mechanical pre-pruning (zero NPU cost — the real token saver) ───────────
STOPWORDS = set("""a an and are as at be but by for from has have in is it its of on or
that the this to was were will with about after all also any can could do does each
for how into just more most not only other over so some such than then there these
they their them then this those through under up very what when where which who why
would you your""".split())


def prune_relevant(content: str, query: str, max_chars: int = None) -> str:
    """Keep only text blocks that mention query keywords. Pure regex scoring —
    runs before any Gemma call, so the NPU only sees on-topic content.

    Blocks = lines/paragraphs. A block survives if it contains ≥1 query keyword
    (word-boundary, case-insensitive) OR is a heading. Surviving blocks are kept
    in original order, then capped at max_chars."""
    max_chars = max_chars or MAX_PAGE_EXTRACT_CHARS
    keywords = [w.lower() for w in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9+-]{2,}", query)
                if w.lower() not in STOPWORDS and len(w) > 2]
    if not keywords:
        return content[:max_chars]
    # also add refined-ish synonyms: npu→npu, gpu→gpu are covered; keep simple
    pattern = re.compile(r"(?<![a-zA-Z0-9])(?:%s)(?![a-zA-Z0-9])" % "|".join(
        re.escape(k) for k in keywords), re.IGNORECASE)

    blocks = re.split(r"\n{2,}", content)
    kept, budget = [], 0
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        is_heading = b.startswith("#")
        if is_heading or pattern.search(b):
            kept.append(b)
            budget += len(b)
            if budget >= max_chars:
                break
    if not kept:
        return content[:max_chars]  # fallback: nothing matched — keep head
    return "\n\n".join(kept)[:max_chars]


def has_numbers(text: str) -> bool:
    return bool(re.search(r"\d", text))


def summarize_page(query: str, title: str, url: str, content: str, model: str) -> str:
    """Quote-anchored extraction: facts + numbers as JSON-backed markdown.
    No merge step — every note stays a pure transcription of the page.

    KEY: content is mechanically pruned to on-topic blocks FIRST (prune_relevant),
    so Gemma only sees relevant text — not nav, footers, or related articles.
    Extraction cost is capped via MAX_PAGE_EXTRACT_CHARS."""
    content = prune_relevant(content, query)
    chunks = chunk_text(content)
    facts, numbers = [], []
    for i, chunk in enumerate(chunks, 1):
        user = f"Page: {title} ({url})\n\n[section {i} of {len(chunks)}]\n{chunk}"
        facts += extract_json_list(FACT_SYSTEM, user, model, stage="facts", max_tokens=1500)
        # numbers pass only if the chunk actually contains digits — skips ~half the calls
        if has_numbers(chunk):
            numbers += extract_json_list(NUMBER_SYSTEM, user, model, stage="numbers", max_tokens=900)
        time.sleep(0.3)

    lines = [f"# {title}", "", f"Source: {url}", ""]
    lines.append("## Facts (quote-anchored)")
    if facts:
        for f in facts:
            fact = (f.get("fact") or "").strip()
            quote = (f.get("quote") or "").strip()
            if fact and quote:
                lines.append(f"- **{fact}**")
                lines.append(f"  > {quote}")
    else:
        lines.append("_No quotable facts extracted._")
    lines.append("")
    lines.append("## Numbers")
    if numbers:
        for n in numbers:
            val = (n.get("value") or "").strip()
            ctx = (n.get("context") or "").strip()
            if val:
                lines.append(f"- **{val}** {n.get('unit', '').strip()}")
                if ctx:
                    lines.append(f"  > {ctx}")
    else:
        lines.append("_No numbers stated._")
    lines.append("")
    return "\n".join(lines)


def extract_links(query: str, title: str, content: str, model: str) -> list:
    """Gemma EXTRACTS links + anchor context only — no scoring (BM25 does that).
    Returns [{url, title, anchor, context}]."""
    content = prune_relevant(content, query, max_chars=18000)
    links = extract_json_list(RANK_SYSTEM, f"Query: {query}\nPage: {title}\n\n{content}",
                              model, stage="links", max_tokens=700)
    out = []
    for l in links:
        if not isinstance(l, dict):
            continue
        url = (l.get("url") or "").strip()
        if url:
            out.append({"url": url,
                        "title": l.get("title", ""),
                        "anchor": l.get("anchor", l.get("title", "")),
                        "context": l.get("context", "")})
    return out


def synthesize(query: str, notes: list, model: str) -> str:
    blob = "\n\n---\n\n".join(notes)
    chunks = chunk_text(blob, CHUNK_CHARS * 2)
    if len(chunks) == 1:
        return gemma_chat_retry(SYNTH_SYSTEM, f"Research query: {query}\n\nEvidence notes:\n{blob}",
                                model=model, max_tokens=2000, temperature=0.1, stage="synthesis")
    partials = []
    for c in chunks:
        partials.append(gemma_chat_retry(SYNTH_SYSTEM, f"Research query: {query}\n\nEvidence notes (partial):\n{c}",
                                         model=model, max_tokens=1200, temperature=0.1, stage="synthesis"))
    return gemma_chat_retry(SYNTH_SYSTEM, f"Merge these partial syntheses for query '{query}':\n\n" +
                            "\n\n---\n\n".join(partials), model=model, max_tokens=2000,
                            temperature=0.1, stage="synthesis")


# ── Session tree manager ────────────────────────────────────────────────────
def slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:60] or "research"


def norm_url(u: str) -> str:
    u = urllib.parse.urlsplit(u)
    qs = urllib.parse.parse_qsl(u.query, keep_blank_values=True)
    qs = [(k, v) for k, v in qs if k not in ("utm_source", "utm_medium", "utm_campaign", "snr")]
    return urllib.parse.urlunsplit((u.scheme, u.netloc, u.path, urllib.parse.urlencode(qs), ""))


class Session:
    def __init__(self, out_dir: Path, query: str, model: str):
        self.root = out_dir / slugify(query)
        self.root.mkdir(parents=True, exist_ok=True)
        for sub in ("01_search", "02_pages", "03_notes", "04_links", "05_synthesis"):
            (self.root / sub).mkdir(exist_ok=True)
        self.state_path = self.root / "session.json"
        self.query = query
        self.model = model
        self.state = self._load_state()

    def _load_state(self) -> dict:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text())
            except Exception:
                pass
        return {
            "query": self.query, "model": self.model, "created": datetime.now().isoformat(),
            "round": 0, "visited": [], "frontier": [], "errors": [], "pages_fetched": 0,
            "searches": 0,
        }

    def save(self):
        self.state_path.write_text(json.dumps(self.state, indent=2))
        self.write_tree()

    def write_tree(self):
        lines = [f"# Research session: {self.query}", "",
                 f"- model: {self.model}", f"- rounds: {self.state['round']}",
                 f"- pages fetched: {self.state['pages_fetched']}",
                 f"- visited: {len(self.state['visited'])} URLs", ""]
        for sub in ("01_search", "02_pages", "03_notes", "04_links", "05_synthesis"):
            d = self.root / sub
            files = sorted(d.glob("*.md")) if d.exists() else []
            lines.append(f"## {sub}/ ({len(files)})")
            for f in files:
                lines.append(f"- [{f.name}]({sub}/{f.name})")
            lines.append("")
        if (self.root / "06_stats.md").exists():
            lines.append("## telemetry")
            lines.append("- [06_stats.md](06_stats.md)")
            lines.append("")
        (self.root / "tree.md").write_text("\n".join(lines))

    def write(self, sub: str, filename: str, content: str):
        (self.root / sub / filename).write_text(content)

    def mark_visited(self, url: str):
        self.state["visited"].append(norm_url(url))
        self.state["visited"] = list(dict.fromkeys(self.state["visited"]))
        self.state["pages_fetched"] += 1

    def add_links(self, links: list):
        for l in links:
            raw_url = (l.get("url") or "").strip()
            if not raw_url:
                continue
            # scheme guard: Gemma sometimes emits bare domains (www.amd.com)
            if not re.match(r"^https?://", raw_url):
                raw_url = "https://" + raw_url
            u = norm_url(raw_url)
            if u in self.state["visited"] or any(f["url"] == u for f in self.state["frontier"]):
                continue
            self.state["frontier"].append({
                "url": u, "title": l.get("title", ""), "score": l.get("score", 0),
                "reason": l.get("reason", ""), "added_round": self.state["round"],
            })
        self.state["frontier"].sort(key=lambda x: -x["score"])


# ── deep research loop ──────────────────────────────────────────────────────
def run(query: str, model: str, max_rounds: int, pages_per_round: int, max_pages: int,
        out_dir: Path, no_refine: bool, verbose: bool, concurrency: int = 2,
        gemma_rank_top: int = 10) -> Session:
    sess = Session(out_dir, query, model)
    frontier = sess.state["frontier"]
    visited = set(sess.state["visited"])

    # Round 0: refine + search + CONTENT-based deterministic rank
    if sess.state["round"] == 0:
        sub_queries = [query] if no_refine else refine_query(query, model)
        plan = f"# Research plan\n\nQuery: {query}\n\nRefined sub-queries:\n" + "\n".join(f"- {q}" for q in sub_queries) + "\n"
        sess.write("", "00_plan.md", plan)
        print(f"[plan] refined into {len(sub_queries)} sub-queries")
        all_candidates = []
        for i, sq in enumerate(sub_queries, 1):
            try:
                results = ddgs_search(sq, max_results=8)
            except Exception as e:
                sess.state["errors"].append(f"ddgs '{sq}': {e}")
                print(f"  [search] '{sq}' FAILED: {e}")
                continue
            body = f"# Search: {sq}\n\n" + "\n".join(
                f"- [{r['title']}]({r['url']})\n  {r['snippet'][:200]}" for r in results) + "\n"
            sess.write("01_search", f"{i:03d}_{slugify(sq)}.md", body)
            for r in results:
                r["sub_query"] = sq
                all_candidates.append(r)
            print(f"  [search] '{sq}': {len(results)} results")
            time.sleep(DDGS_DELAY)
        # content preview: fetch each candidate's head content for REAL ranking
        print(f"  [preview] fetching head content of {len(all_candidates)} candidates for ranking...")
        for c in all_candidates:
            c["_preview"] = content_preview(c["url"])
        ranked = rank_with_content(all_candidates, query)
        content_scored = sum(1 for c in ranked if c.get("content_scored"))
        for c in ranked:
            u = norm_url(c["url"])
            if u in visited or any(f["url"] == u for f in frontier):
                continue
            frontier.append({"url": u, "title": c["title"], "snippet": c.get("snippet", ""),
                             "score": c["final_score"], "reason": f"bm25={c['bm25']} ddgs={c['ddgs_score']}",
                             "added_round": 0})
        print(f"  [rank] frontier seeded with {len(ranked)} candidates "
              f"({content_scored}/{len(ranked)} content-scored, deterministic)")
        sess.state["round"] = 1
        sess.state["searches"] = 1
        sess.save()

    # Rounds
    while sess.state["round"] <= max_rounds:
        if not flm_alive():
            sess.state["errors"].append("FATAL: FLM not responding at round start — aborting")
            sess.save()
            print("[loop] FLM unresponsive — aborting (re-run same query to resume)", file=sys.stderr)
            break

        # ── re-search trigger: exhausted frontier OR low source diversity ──
        unvisited_now = [f for f in sess.state["frontier"] if f["url"] not in sess.state["visited"]]
        best_score = max((f.get("score", 0) for f in unvisited_now), default=0.0)
        covered_domains = sorted({
            urllib.parse.urlsplit(n.split("Source: ")[1].strip())[1] if "Source: " in n else ""
            for n in (f.read_text() for f in (sess.root / "03_notes").glob("*.md"))
            if "Source: " in n
        })
        covered_domains = [d for d in covered_domains if d]
        searches_done = sess.state.get("searches", 1)
        need_more = (best_score < SEARCH_FLOOR or len(covered_domains) < MIN_DOMAINS) \
                    and searches_done < MAX_SEARCHES
        if need_more:
            new_q = gap_query(query, covered_domains, model)
            print(f"  [research] frontier weak (best={best_score:.2f}, domains={len(covered_domains)}/{MIN_DOMAINS}) "
                  f"— re-searching: '{new_q[:60]}'")
            try:
                results = ddgs_search(new_q, max_results=8)
            except Exception as e:
                sess.state["errors"].append(f"ddgs re-search '{new_q}': {e}")
                results = []
            if results:
                for r in results:
                    r["_preview"] = content_preview(r["url"])
                ranked = rank_with_content(results, query)
                added = 0
                for c in ranked:
                    u = norm_url(c["url"])
                    if u in sess.state["visited"] or any(f["url"] == u for f in sess.state["frontier"]):
                        continue
                    sess.state["frontier"].append({"url": u, "title": c["title"], "snippet": c.get("snippet", ""),
                                                   "score": c["final_score"],
                                                   "reason": f"research#{searches_done+1} bm25={c['bm25']} ddgs={c['ddgs_score']}",
                                                   "added_round": sess.state["round"]})
                    added += 1
                print(f"  [research] +{added} new candidates merged into frontier")
            sess.state["searches"] = searches_done + 1
            sess.save()

        sess.state["frontier"].sort(key=lambda x: -x["score"])
        round_links = [f for f in sess.state["frontier"] if f["url"] not in sess.state["visited"]][:pages_per_round]
        if not round_links:
            print("[loop] frontier empty — stopping")
            break
        if sess.state["pages_fetched"] >= max_pages:
            print(f"[loop] page budget reached ({max_pages}) — stopping")
            break

        print(f"\n=== round {sess.state['round']}: fetching {len(round_links)} pages ===")
        urls = [f["url"] for f in round_links]
        fetched = asyncio.run(fetch_pages(urls, max_concurrent=concurrency, verbose=verbose))

        for link in round_links:
            url = link["url"]
            sess.mark_visited(url)
            fr = fetched.get(url, {})
            ok, content = fr.get("ok"), fr.get("content", "")
            fname = f"{sess.state['pages_fetched']:03d}_{slugify(link['title'] or url)}.md"

            if not ok or not content or len(content) < 300:
                err = f"fetch failed/short: {url} — {str(content)[:120]}"
                sess.state["errors"].append(err)
                print(f"  [fetch] {url} FAILED")
                sess.write("02_pages", fname, f"# {url}\n\nERROR: {err}\n")
                sess.save()
                continue

            sess.write("02_pages", fname, f"# {link['title']} — {url}\n\n{content}")
            print(f"  [fetch] {url} ({len(content)//1000}KB markdown)")
            # re-rank this page on its REAL content (BM25 on pruned text)
            pruned_for_rank = prune_relevant(content, query, max_chars=CONTENT_PREVIEW_CHARS)
            rerank_idx = BM25Index()
            rerank_idx.add("page", pruned_for_rank)
            link["score"] = round(rerank_idx.score("page", query), 4)
            link["reason"] = (link.get("reason", "") + f" | content_bm25={link['score']}").strip()
            try:
                note = summarize_page(query, link["title"], url, content, model)
            except Exception as e:
                sess.state["errors"].append(f"summarize {url}: {e}")
                note = f"# {link['title']} ({url})\n\nSUMMARY FAILED: {e}"
            header = f"# {link['title']}\n\nSource: {url}\nRelevance: {link.get('score', 0):.2f} — {link['reason']}\n\n"
            sess.write("03_notes", fname, header + note + "\n")

            try:
                new_links = extract_links(query, link["title"], content, model)
            except Exception as e:
                sess.state["errors"].append(f"extract links {url}: {e}")
                new_links = []
            # deterministic scoring: BM25 on anchor/title + parent provenance
            new_links = score_discovered_links(new_links, query, parent_score=link.get("score", 0))
            sess.add_links(new_links)
            print(f"  [gemma] extracted {len(new_links)} links → BM25-scored")

        # Gemma steering: triage the top slice ONCE per round (≤ gemma_rank_top items)
        unvisited = [f for f in sess.state["frontier"] if f["url"] not in sess.state["visited"]]
        unvisited.sort(key=lambda x: -x.get("score", 0))
        if unvisited:
            verdicts = steer_frontier(query, unvisited, model, max_items=gemma_rank_top)
            applied = {"priority": 0, "skip": 0, "visit": 0}
            for v in verdicts:
                url = norm_url(v.get("url", ""))
                action = v.get("action", "")
                for f in sess.state["frontier"]:
                    if f["url"] == url:
                        if action == "priority":
                            f["score"] = f.get("score", 0) + 1.5
                            f["reason"] = (f.get("reason", "") + " | gemma:priority").strip()
                            applied["priority"] += 1
                        elif action == "skip":
                            sess.state["frontier"] = [x for x in sess.state["frontier"] if x["url"] != url]
                            applied["skip"] += 1
                        else:
                            applied["visit"] += 1
                        break
            print(f"  [gemma] steered top {min(len(unvisited), gemma_rank_top)}: "
                  f"{applied['priority']} priority, {applied['skip']} skipped, {applied['visit']} kept")

        links_body = "\n".join(
            f"- [{f['title'] or f['url']}]({f['url']}) — {f.get('score', 0):.2f}: {f['reason']}"
            for f in sess.state["frontier"] if f["added_round"] == sess.state["round"]
        ) or "_none_"
        sess.write("04_links", f"round_{sess.state['round']:03d}.md",
                   f"# Links discovered in round {sess.state['round']}\n\n{links_body}\n")
        sess.state["round"] += 1
        sess.save()

    # Synthesis
    print("\n=== synthesis ===")
    notes = []
    for f in sorted((sess.root / "03_notes").glob("*.md")):
        notes.append(f.read_text())
    if notes:
        try:
            findings = synthesize(query, notes, model)
        except Exception as e:
            findings = f"Synthesis failed: {e}"
        sess.write("05_synthesis", "findings.md", findings)
        print("[synthesis] findings.md written")
    else:
        print("[synthesis] no notes to synthesize")
        sess.write("05_synthesis", "findings.md", "_No pages were successfully summarized._\n")

    sess.save()
    # telemetry report
    sess.write("", "06_stats.md", STATS.report())
    print("\n" + "=" * 52)
    print("TELEMETRY")
    print("=" * 52)
    print(f"  gemma calls:      {len(STATS.calls)}")
    print(f"  prompt tokens:    {STATS.total_prompt_tokens:,}")
    print(f"  completion tokens:{STATS.total_completion_tokens:,}")
    print(f"  total tokens:     {STATS.total_tokens:,}")
    print(f"  wall time:        {STATS.wall_time:.1f}s")
    print(f"  avg decode speed: {STATS.avg_tps():.1f} tok/s (FLM-measured)")
    print(f"  → full breakdown: {sess.root}/06_stats.md")
    print(f"\nDONE. Session at: {sess.root}")
    print(f"  tree.md, 03_notes/, 05_synthesis/findings.md ← read these first")
    if sess.state["errors"]:
        print(f"  {len(sess.state['errors'])} errors logged (see session.json)")
    return sess


def run_safe(*args, **kwargs) -> Session:
    """run() with a crash guard: any top-level exception is logged to session.json
    instead of dying silently (the OOM-kill failure mode we hit before)."""
    sess = Session(kwargs["out_dir"], kwargs["query"], kwargs["model"])
    try:
        return run(*args, **kwargs)
    except BaseException as e:
        sess.state["errors"].append(f"FATAL: {type(e).__name__}: {e}")
        sess.save()
        print(f"\n[FATAL] {type(e).__name__}: {e}", file=sys.stderr)
        print(f"  logged to {sess.state_path}; re-run same query to resume", file=sys.stderr)
        raise


# ── CLI ─────────────────────────────────────────────────────────────────────
def probe_flm():
    if not os.environ.get("FLM_BASE_URL"):
        try:
            with urllib.request.urlopen(FLM_BASE_URL + "/models", timeout=5):
                pass
        except Exception as e:
            print(f"FLM not reachable at {FLM_BASE_URL}: {e}", file=sys.stderr)
            sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description="crawl4ai tool: one-shot fetch OR autonomous Gemma research loop")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_fetch = sub.add_parser("fetch", help="one-shot URL fetch → clean markdown (no Gemma)")
    p_fetch.add_argument("urls", nargs="+", help="one or more URLs to crawl")
    p_fetch.add_argument("-o", "--output", help="write to file (appends .md if no ext)")
    p_fetch.add_argument("--no-prune", action="store_true", help="raw markdown, no content filtering")
    p_fetch.add_argument("--bm25", action="store_true", help="use BM25 content filter (keyword-aware)")
    p_fetch.add_argument("--query", help="query string for BM25 filter (required with --bm25)")
    p_fetch.add_argument("--verbose", action="store_true")
    p_fetch.add_argument("--headless", action="store_true", default=True, help="headless browser (default: on)")
    p_fetch.add_argument("--no-headless", dest="headless", action="store_false", help="show browser window")
    p_fetch.set_defaults(func=cmd_fetch)

    p_res = sub.add_parser("research", help="deep research loop (Gemma + DDGS + crawl4ai)")
    p_res.add_argument("query", help="research query")
    p_res.add_argument("--model", default=MODEL, help=f"FLM model (default: {MODEL})")
    p_res.add_argument("--max-rounds", type=int, default=5)
    p_res.add_argument("--pages-per-round", type=int, default=2)
    p_res.add_argument("--max-pages", type=int, default=30)
    p_res.add_argument("--concurrency", type=int, default=2, help="max concurrent browser fetches (fallback only)")
    p_res.add_argument("--gemma-rank-top", type=int, default=10,
                       help="max frontier items Gemma steers per round (default 10; DeepSeek's call)")
    p_res.add_argument("--out-dir", default=str(Path.home() / ".hermes" / "crawl_sessions"))
    p_res.add_argument("--no-refine", action="store_true", help="skip Gemma query refinement")
    p_res.add_argument("--verbose", action="store_true")
    p_res.set_defaults(func=lambda a: run_safe(query=a.query, model=a.model,
                                               max_rounds=a.max_rounds, pages_per_round=a.pages_per_round,
                                               max_pages=a.max_pages, out_dir=Path(a.out_dir),
                                               no_refine=a.no_refine, verbose=a.verbose,
                                               concurrency=a.concurrency, gemma_rank_top=a.gemma_rank_top))

    args = ap.parse_args()
    if args.mode == "research":
        probe_flm()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
