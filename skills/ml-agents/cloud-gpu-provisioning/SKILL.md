---
name: cloud-gpu-provisioning
description: Research, compare, and provision cloud GPU instances for ML training. Covers cost analysis across providers (RunPod, Jarvis Labs, Vast.ai, Lambda), storage architecture decisions (ephemeral vs persistent), dataset acquisition, and model weight persistence strategies.
---

# Cloud GPU Provisioning for ML Training

Research methodology for evaluating and selecting cloud GPU instances, storage, and data workflows.

## When to use

- User asks about GPU cloud pricing or comparison between providers
- User wants to understand storage costs (ephemeral vs persistent)
- User is planning ML training infrastructure on rented GPUs
- User needs to move datasets or weights between local/cloud/storage

## Consumer GPU pricing research (RTX 4090 tier)

### Sources of truth

- **GridStackHub** (`gridstackhub.ai/providers/<provider>-rtx4090`) — live aggregated pricing, 90-day history, cross-provider comparison tables
- **Provider pricing pages** — RunPod (`/pricing`, `/gpu-models/rtx-4090`), Jarvis Labs (`/pricing`), Vast.ai
- **GPU Finder** (`gpufinder.dev`) — cross-provider GPU price comparison
- **DeployBase** (`deploybase.ai/articles/gpu-pricing`) — written pricing guides with per-month math
- **Provider docs** — check `/storage/network-volumes`, `/filestorage`, `/pods/storage/types` for storage pricing

### Typical RTX 4090 pricing (as of mid-2026)

| Provider | Tier | $/hr | Notes |
|----------|------|------|-------|
| RunPod | Community Cloud | $0.34 | Cheapest, no SLA, variable availability |
| RunPod | Secure Cloud | $0.69 | Datacenter-grade, SLA |
| Jarvis Labs | On-Demand | $0.49 | Stable pricing, India/EU regions |
| Vast.ai | Spot | $0.13-0.25 | Marketplace, price volatility, interruption risk |

### Storage cost comparison

| Provider | Persistent storage | Rate | Notes |
|----------|-------------------|------|-------|
| RunPod | Network volume | $0.07/GB/mo (<1TB), $0.05/GB/mo (>1TB) | Survives pod termination, shareable |
| RunPod | Container disk | $0.10/GB/mo (running), $0.20/GB/mo (stopped) | Ephemeral, lost on stop |
| Jarvis Labs | File storage | $0.10/GB/mo ($0.00014/GB/hr) | Survives instance termination |
| Hugging Face Hub | Model repos | Free (public & private) | Ideal for trained weights |

## Storage architecture — three tiers

Every cloud GPU provider has essentially the same layered model:

1. **Ephemeral / container disk** (included or cheap)
   - OS, temp files, cache
   - Wiped on stop/restart
   - RunPod: container disk, Jarvis: `/home` directory

2. **Semi-persistent / volume disk** (medium cost)
   - Survives stop/restart but deleted on pod/instance termination
   - RunPod: volume disk at `/workspace` — $0.10/GB/mo running, $0.20/GB/mo stopped
   - Best for active datasets and checkpoints during a project

3. **Fully persistent / network volume** (lower long-term cost)
   - Survives termination, shareable across pods
   - RunPod: network volume at $0.07/GB/mo
   - Jarvis Labs: file storage at $0.10/GB/mo
   - Best for dataset staging and long-lived projects

## Dataset acquisition patterns

### Torbox (debrid/seedbox) — limited usefulness

- Good for: fast download of cached public torrent datasets
- WebDAV is **read-only** — cannot write weights back
- Files expire after cache period (30 days on Pro)
- Not suitable as persistent storage or streaming source during training

### Direct download
- `wget` / `curl` from Hugging Face, academic mirrors, S3
- `huggingface-cli download` or `snapshot_download()` from `huggingface_hub`

### Hugging Face Hub streaming
- `load_dataset(..., streaming=True)` — trains without downloading full dataset to disk
- Saves storage while iterating on model architecture

## Model weight persistence strategy

| Purpose | Best option | Cost |
|---------|-------------|------|
| Active training checkpoints | RunPod volume disk or network volume | $7-10/100GB/mo |
| Final trained weights (permanent) | Hugging Face Hub repos | Free |
| Intermediate checkpoints between runs | RunPod network volume (pause GPU, keep storage) | $7/TB/mo |
| Local backup | Download to local machine or NAS | One-time transfer |

## Model size → hardware mapping

When a user asks what GPU they need for a specific model, use this table. All figures are for **4-bit quantized inference** (memory doubles for fine-tuning due to optimizer states + gradients):

| Model | Total params | Active/token | 4-bit VRAM | Min GPU (inference) | Fine-tune |
|-------|-------------|--------------|------------|-------------------|-----------|
| 7B (LLaMA 3, Mistral) | 7B | 7B (dense) | ~4 GB | **1× RTX 4090** ✅ | 1× RTX 4090 LoRA |
| 13B | 13B | 13B (dense) | ~7 GB | 1× RTX 4090 ✅ | 2× RTX 4090 |
| 70B | 70B | 70B (dense) | ~35 GB | **1× A100 80GB** ✅ | 2-4× A100 |
| DeepSeek V4-Flash | 284B | ~13B (MoE) | ~142 GB | **2× A100 80GB** | 4-6× A100 |
| Kimi K2 | 1T | ~32B (MoE) | ~500 GB | **6-7× A100 80GB** | 12+ A100 |
| DeepSeek V4-Pro | 1.6T | ~49B (MoE) | ~800 GB | **10× A100 80GB** | 20+ A100 |
| Kimi K3 | 2.8T | — (MoE) | ~1.4 TB | Multi-node only | Multi-node only |

**Key:** MoE models need all experts in memory — total params (not active) determines hardware. Multi-GPU cost scales linearly per GPU.

## ARC-AGI does NOT use GPU training

ARC-AGI (v1/v2) is solved via **LLM API-based program synthesis**, not GPU compute:

- **Berman (2025)**: ~$8.42/task, ~80% — Claude generates + tests 500 Python functions
- **epang080516 (2025)**: ~$2.56/task, 77.1% — DreamCoder-inspired library with LLM search
- **OpenAI o3**: ~$200/task, ~87% — brute force test-time compute

For small budgets (~1000 INR/$12): use GPT-4o-mini at ~$0.15/task, clone the open-source repo, run on local CPU. No GPU rental needed. For ARC-AGI-3 (interactive), see the `arc-agi-3` skill.

### Hugging Face Hub workflow

```python
from huggingface_hub import HfApi, snapshot_download
from huggingface_hub import create_repo, upload_folder

# Push trained weights
api = HfApi()
api.create_repo(repo_id="your-username/model-name", private=True)
api.upload_folder(
    folder_id="your-username/model-name",
    folder_path="/workspace/output/checkpoint-1000",
)

# Pull weights on new instance
snapshot_download(repo_id="your-username/model-name")
```

## Pitfalls

- **Storage billing while stopped**: RunPod volume disk charges $0.20/GB/mo when pod is stopped (double the running rate). Network volume charges $0.07/GB/mo regardless. Use network volume for long-term data you don't want to pay inflated stopped rates on.
- **RunPod Community Cloud has no SLA**: pods can be preempted. Use Secure Cloud for production training.
- **Jarvis Labs file storage is provisioned capacity**: You pay for allocated size, not used size. Size can only be increased, never decreased.
- **Hugging Face Hub has repo size limits**: Very large datasets may need Git LFS or alternative storage.
- **Torbox WebDAV is read-only**: You cannot upload trained weights back to TorBox. It's download-only via the WebDAV mount.
- **Always check current pricing**: GPU cloud pricing changes frequently. GridStackHub's 90-day history helps identify trends. Always verify against the provider's live pricing page before committing.
