# FLM Embedding Reranking for Crawled Content

Reusable script for post-crawl semantic reranking using `embed-gemma:300m` on the NPU.

## Prerequisites

FLM server must be running with `--embed 1` to load the embedding model alongside the LLM:
```bash
flm.exe serve qwen3:1.7b --host 0.0.0.0 --port 50001 --embed 1
```

The `embed-gemma` model appears on `v1/models` only when `--embed 1` is active. Without it, the embeddings endpoint returns null.

## Script

```python
"""rerank_crawl_results.py — semantic reranking with FLM embeddings.

Usage:
  python rerank_crawl_results.py <crawl_output.md> "your query" [--top-k 5] [--threshold 0.3]

Takes a markdown file of crawled content, splits into sections/chunks,
embeds each with embed-gemma:300m, ranks by cosine similarity to query.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
from openai import OpenAI


FLM_BASE_URL = "http://172.29.192.1:50001/v1"


def split_into_chunks(text: str, min_chars: int = 200) -> list[dict]:
    """Split markdown into chunks by headings, each with source heading."""
    chunks = []
    current_heading = "Top"
    current_parts = []

    for line in text.split("\n"):
        if line.startswith("#") and line.strip():
            if current_parts:
                content = "\n".join(current_parts).strip()
                if len(content) >= min_chars:
                    chunks.append({"heading": current_heading, "text": content})
            current_heading = line.lstrip("#").strip()
            current_parts = []
        else:
            current_parts.append(line)

    if current_parts:
        content = "\n".join(current_parts).strip()
        if len(content) >= min_chars:
            chunks.append({"heading": current_heading, "text": content})

    return chunks


def embed(texts: list[str], client: OpenAI) -> list[list[float]]:
    """Batch embed texts with embed-gemma."""
    resp = client.embeddings.create(model="embed-gemma", input=texts)
    return [r.embedding for r in resp.data]


def cosine_sim(a: list[float], b: list[float]) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def main():
    parser = argparse.ArgumentParser(description="Semantic reranking via FLM embeddings")
    parser.add_argument("input", help="Markdown file with crawled content")
    parser.add_argument("query", help="Search query for reranking")
    parser.add_argument("--top-k", type=int, default=5, help="Keep top-K chunks")
    parser.add_argument("--threshold", type=float, default=0.3, help="Min similarity score (0-1)")
    parser.add_argument("--output", "-o", help="Write top chunks to file")
    args = parser.parse_args()

    text = Path(args.input).read_text(encoding="utf-8")
    chunks = split_into_chunks(text)

    if not chunks:
        print("No chunks found (min_chars=200). Try a smaller threshold.")
        sys.exit(1)

    print(f"Split into {len(chunks)} chunks. Embedding...", file=sys.stderr)

    client = OpenAI(base_url=FLM_BASE_URL, api_key="flm")
    query_vec = embed([args.query], client)[0]
    chunk_vecs = embed([c["text"] for c in chunks], client)

    for chunk, vec in zip(chunks, chunk_vecs):
        chunk["score"] = round(cosine_sim(query_vec, vec), 4)

    chunks.sort(key=lambda x: x["score"], reverse=True)
    top = [c for c in chunks if c["score"] >= args.threshold][:args.top_k]

    print(f"\nTop {len(top)} chunks (threshold >= {args.threshold}):\n")
    for i, c in enumerate(top, 1):
        print(f"=== [{i}] score={c['score']:.4f} — {c['heading']} ===")
        print(c["text"][:600])
        if len(c["text"]) > 600:
            print("... (truncated)")
        print()

    if args.output:
        out = Path(args.output)
        content = "\n\n".join(
            f"# [{c['score']:.4f}] {c['heading']}\n\n{c['text']}" for c in top
        )
        out.write_text(content)
        print(f"Written to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
```

## Limitations

- `embed-gemma:300m` has MTEB Retrieval score ~38-42 — decent but beaten by CPU models 1/10th its size (bge-small, gte-small). For production RAG quality, consider `sentence-transformers` on CPU instead.
- Batch size: FLM's `/v1/embeddings` handles one-at-a-time best. For 50+ chunks, expect ~1-2s per chunk.
- The NPU embedding model is a convenience layer when FLM is already running. For dedicated embedding workloads, a CPU-based model is faster and more accurate.
