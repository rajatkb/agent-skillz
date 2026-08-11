---
name: cloud-gpu-cost-analysis
description: Research and compare cloud GPU pricing across providers (RunPod, Vast.ai, Jarvis Labs, TensorDock, Lambda), factoring in GPU compute, storage architecture, bandwidth, and hidden costs. Produce actionable per-workload recommendations.
---

# Cloud GPU Cost Analysis

Research approach for comparing cloud GPU providers for ML training/inference workloads.

## When to use

User asks to compare GPU cloud providers, find cheapest RTX 4090 / A100 / H100 setup, evaluate total cost for a training workload, or understand storage pricing differences between providers.

## Research workflow

### 1. Identify the target GPU and workload

Key questions to clarify first:
- Which GPU (RTX 4090, A100, H100, etc.)?
- Workload type: training vs inference vs fine-tuning?
- Approximate hours per month?
- Data footprint (datasets, checkpoints, model weights)?
- Is interruptibility acceptable (spot/preemptible) or need guaranteed uptime?

### 2. Gather live pricing

- `web_search` for current pricing — include provider name, GPU model, "price per hour", current year
- Cross-reference against aggregators: GridStackHub, GPU Finder, DeployBase
- Note the **date** of the data — GPU cloud pricing changes frequently
- Check provider's own pricing page for official rates

### 3. Identify all cost components — not just GPU

Never quote GPU-only pricing without checking these hidden costs:

| Component | Typical range | Notes |
|-----------|--------------|-------|
| **GPU compute** | $0.16–$3.80/hr | Varies wildly by GPU and tier |
| **Container/volume disk** | $0.07–$0.20/GB/mo | Ephemeral vs persistent pricing differs |
| **Network/persistent storage** | $0.07–$0.10/GB/mo | Survives pod/instance deletion |
| **Bandwidth/egress** | Free–$0.12/GB | Some providers (Jarvis, HF Hub) have free egress |
| **Idle/stopped storage** | $0.10–$0.20/GB/mo | RunPod charges more for stopped volume disks |
| **Reserved/spot discount** | 20–56% off | Ask if user's workload can tolerate interruption |

### 4. Storage architecture — the biggest hidden cost

Each provider has a different storage model. Always clarify:

**RunPod:**
- Container disk: ephemeral (lost on stop/restart), $0.10/GB/mo
- Volume disk: survives stop, lost on pod termination, $0.10/GB/mo (running), $0.20/GB/mo (stopped)
- Network volume: truly persistent across pod deletion, $0.07/GB/mo — cheapest per-GB option
- Network volumes only work with Secure Cloud, NOT Community Cloud

**Jarvis Labs:**
- Local `/home` storage: ephemeral, included in GPU price
- File storage (persistent): $0.10/GB/mo, mounted at `/home/jl_fs`
- Max 2TB per volume
- Supports "Paused" state where compute billing stops but storage continues

**Vast.ai:**
- Container storage: set at creation, varies by host, charged per GB continuously
- Volumes: persistent but tied to physical machine (cannot migrate)
- Storage rates set by each host — varies widely
- Storage charges continue when instance is stopped

### 5. Present total cost, not just GPU price

Format: **GPU cost (hrs × rate) + Storage cost (GB × rate/month)** = monthly total

Include a table showing 100hrs-monthly and 24/7 scenarios.

### 6. Consider auxiliary storage strategies

- **Hugging Face Hub**: free for public/private repos. Push trained weights → destroy instance → pull later. `snapshot_download()` and `huggingface-cli download` for retrieval. Streaming datasets: `load_dataset(streaming=True)`.
- **Torbox**: debrid/seedbox service. WebDAV is read-only. Good for torrenting public datasets but not for persistent ML storage or writing back weights. Cache-based (files expire after 30 days on Pro plan).
- **S3-compatible storage**: all major providers support this for backup.

## Pitfalls

- Do not quote GPU-only costs as "total" — storage dominates at >200GB
- Do not assume "ephemeral" means "free" — RunPod charges $0.10/GB/mo for container disk
- Do not assume community/spot tiers support network volumes (RunPod Community Cloud does NOT — network volumes are Secure Cloud only)
- Vast.ai storage pricing is not fixed — it varies per host. Always estimate conservatively
- Check GPU availability in the specific region/datacenter before recommending
- Per-second billing (RunPod, Jarvis) vs per-hour billing (older providers) changes cost math for short runs

## Verification

After recommending a provider:
1. Verify the specific GPU is available at the quoted price in the datacenter region
2. If recommending persistent storage, confirm the storage type supports the user's session-duration needs
3. Factor in Hugging Face Hub for weight storage loop — it eliminates persistent storage costs for model artifacts
