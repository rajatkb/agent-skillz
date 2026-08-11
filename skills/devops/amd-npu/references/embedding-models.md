# Text Embedding Models for NPU / RAG

## Standard Benchmark: MTEB

**[MTEB](https://huggingface.co/spaces/mteb/leaderboard)** (Massive Text Embedding Benchmark) is the standard benchmark for embedding models. It covers 8 task categories:

| Task | What it measures | Relevance to RAG |
|---|---|---|
| **Retrieval** | Ranking relevant docs against distractors (15 datasets) | **Core** — this is what matters for RAG |
| Clustering | Grouping similar texts | Indirect |
| Pair Classification | Semantic similarity of pairs | Indirect |
| Reranking | Re-ranking candidate results | Related but separate |
| STS | Semantic textual similarity | Related |
| Summarization | Summary quality scoring | Niche |
| Classification | Label accuracy from embeddings | Useful |
| Bitext Mining | Cross-lingual alignment | Niche |

For RAG, **focus on the Retrieval subtask score**, not the MTEB overall average.

## Embedding Models on FLM

### embed-gemma:300m (NPU-accelerated)

Google's dedicated embedding model, 300M parameters. Listed as `embed-gemma:300m` in FLM's catalog.

| Property | Value |
|---|---|
| Quantization | Q4_1 |
| Max Chunk Size | **2048** tokens per input (not 512 — confirmed in FLM docs) |
| Dimensions | 768 |
| Tool Calling | No (not a chat model) |

- **MTEB Retrieval:** ~38-42 (moderate — usable for simple RAG)
- **MTEB Overall:** ~46-48
- **Endpoint:** `POST /v1/embeddings` (OpenAI-compatible)

### How to use from WSL

**Critical usage pattern:** The embedding model does NOT work standalone in CLI mode. It must be loaded **alongside** a generation LLM in server mode:

```bash
# 1. Pull the model first (one-time)
flm.exe pull embed-gemma:300m

# 2. Serve it WITH a chat model using --embed 1 flag
flm.exe serve qwen3:1.7b --host 0.0.0.0 --port 50001 --embed 1
```

The `--embed 1` flag loads `embed-gemma:300m` in the background alongside the specified LLM. Both models are then available on the same endpoint.

```bash
# 3. Generate embeddings from WSL
GW_IP=$(ip route show default | awk '{print $3}')
curl -s http://$GW_IP:50001/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model":"embed-gemma","input":"Your text here"}'
```

The model name in the API call is `"embed-gemma"` (not the full tag).
```

## Comparison: Alternative Embedding Models

These run on **CPU** (not NPU), but are relevant for context since CPU embeddings can be faster than NPU round-trips for small batch sizes:

| Model | Params | MTEB Retrieval | MTEB Overall | Dimensions | Max Tokens |
|---|---|---|---|---|---|
| bge-small-en-v1.5 | 33M | ~47 | ~57 | 384 | 512 |
| bge-base-en-v1.5 | 102M | ~53 | ~63 | 768 | 512 |
| bge-large-en-v1.5 | 326M | ~54 | ~64 | 1024 | 512 |
| **embed-gemma:300m** | **300M** | **~38-42** | **~46-48** | **768** | **512** |
| text-embedding-3-small (OpenAI) | ~1.3B (est) | ~55 | ~62 | 1536 | 8191 |
| text-embedding-3-large (OpenAI) | ~? | ~60 | ~64 | 3072 | 8191 |
| gte-small | 33M | ~49 | ~60 | 384 | 512 |
| gte-base | 102M | ~53 | ~64 | 768 | 8192 |

Key takeaway: embed-gemma:300m on NPU is beaten by **CPU models a tenth its size** (bge-small 33M has better retrieval scores). The NPU advantage for embeddings is marginal at these sizes — a CPU-based BGE-Small or GTE-Small is often faster and more accurate.

## When to Use NPU Embeddings vs CPU

| Scenario | Recommendation |
|---|---|
| You already serve FLM and want one-less-service | embed-gemma:300m (convenience) |
| Retrieval quality matters > convenience | BGE-Base or GTE-Base on CPU |
| You need <100ms per embedding | BGE-Small on CPU (33M, fits L1 cache) |
| You're embedding 10K+ docs at once | BGE-Base on CPU with batch encoding |
