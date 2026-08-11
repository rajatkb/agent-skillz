#!/usr/bin/env python3
"""OpenReview conference paper crawler (API v2).

Finds papers on a topic at an ML conference, filters to accepted only,
scores title+abstract against keyword weights, prints candidates with
OpenReview forum links. Verified working Aug 2026 against NeurIPS 2024/2025.

Usage:
  python3 openreview_crawl.py --group NeurIPS.cc/2025/Conference \
      --term "expert" --term "mixture of experts" --term "MoE" \
      --kw "nerf:6" --kw "3d:2" --min-score 2 --arxiv

Notes:
  - Use /notes/search ONLY. The bulk /notes endpoint returns 403
    ChallengeRequiredError (bot protection).
  - Search is relevance-ranked & capped: pagination returns far fewer
    unique notes than `count` claims. Add overlapping terms to cover gaps.
  - Keep ~1.2s between requests; after a 429 burst, back off ~30s.
"""
import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

# Default weights: graphics/vision hunting (the common case). Override with --kw.
DEFAULT_KEYWORDS = {
    "nerf": 6, "gaussian splat": 6, "splat": 6, "radiance field": 6,
    "rendering": 5, "ray tracing": 5, "path tracing": 5, "graphics": 4,
    "mesh": 3, "texture": 2, "3d": 2, "scene": 2, "point cloud": 3,
    "avatar": 4, "animation": 3, "image synthesis": 4, "image generation": 3,
    "video generation": 3, "lighting": 3, "surface reconstruction": 4,
    "neural implicit": 4, "view synthesis": 5, "relight": 4, "shading": 4,
    "inverse rendering": 5, "image editing": 3, "super-resolution": 2,
    "3d reconstruction": 4, "volumetric": 3, "radiance": 5, "sdf": 3,
    "human motion": 3, "motion generation": 3, "character": 2, "dance": 3,
}


def search(term, content, group, limit=100, offset=0):
    url = (f"https://api2.openreview.net/notes/search?term={urllib.parse.quote(term)}"
           f"&group={urllib.parse.quote(group)}&content={content}&limit={limit}&offset={offset}")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def score(text, keywords):
    t = (text or "").lower()
    s, hits = 0, []
    for kw, w in keywords.items():
        if kw in t:
            s += w
            hits.append(kw)
    return s, hits


def arxiv_id(title):
    """Resolve arXiv ID for an exact paper title. Returns None if absent."""
    q = urllib.parse.quote(title)
    url = f'http://export.arxiv.org/api/query?search_query=ti:"{q}"&max_results=2'
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        xml = r.read().decode()
    ids = re.findall(r"<id>http://arxiv.org/abs/([\w.\-/]+)</id>", xml)
    return ids[0] if ids else None


def main():
    ap = argparse.ArgumentParser(description="OpenReview conference paper crawler")
    ap.add_argument("--group", required=True, help="e.g. NeurIPS.cc/2025/Conference")
    ap.add_argument("--term", action="append", required=True, help="search term (repeatable)")
    ap.add_argument("--content", default="all", choices=["all", "title", "abstract"])
    ap.add_argument("--pages", type=int, default=6, help="offset pages of 100 per term")
    ap.add_argument("--min-score", type=int, default=2)
    ap.add_argument("--kw", action="append", default=[], help="keyword:weight override (repeatable)")
    ap.add_argument("--include-rejected", action="store_true", help="keep non-accepted venueids")
    ap.add_argument("--arxiv", action="store_true", help="resolve arXiv IDs for finalists")
    args = ap.parse_args()

    keywords = dict(DEFAULT_KEYWORDS)
    for kv in args.kw:
        k, _, w = kv.partition(":")
        keywords[k.strip()] = int(w)

    seen = {}
    for term in args.term:
        for offset in range(0, args.pages * 100, 100):
            try:
                data = search(term, args.content, args.group, 100, offset)
            except Exception as e:
                print(f"term={term!r} offset={offset} ERROR: {e}", file=sys.stderr)
                time.sleep(5)
                continue
            for n in data.get("notes", []):
                seen.setdefault(n.get("forum", n.get("id")), n)
            time.sleep(1.2)

    results = []
    for n in seen.values():
        c = n.get("content", {})
        title = c.get("title", {}).get("value", "")
        abstract = c.get("abstract", {}).get("value", "")
        vid = c.get("venueid", {}).get("value", "")
        if not args.include_rejected and vid != args.group:
            continue
        s, hits = score(title + " " + abstract, keywords)
        if s >= args.min_score:
            results.append({"score": s, "hits": hits, "title": title,
                            "forum": n.get("forum"), "venueid": vid,
                            "abstract": abstract[:400]})

    results.sort(key=lambda x: -x["score"])
    print(f"unique notes collected: {len(seen)}; candidates: {len(results)}")
    for r in results:
        print(f"[{r['score']}] {r['title']}  (venue: {r['venueid']})")
        print(f"   hits: {r['hits']}")
        print(f"   https://openreview.net/forum?id={r['forum']}")
        if args.arxiv:
            aid = arxiv_id(r["title"])
            print(f"   arXiv: {aid or 'none found'}")
            time.sleep(3)  # arXiv API is rate-sensitive
        print(f"   {r['abstract'][:220]}...\n")

    with open("/tmp/openreview_crawl_results.json", "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
