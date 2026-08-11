# Cloud GPU Pricing Snapshot — July 2026

RTX 4090 pricing across major providers, sourced from GridStackHub, DeployBase, and provider pricing pages. **Confirm current rates before quoting** — cloud GPU pricing is volatile.

## Raw GPU Compute (RTX 4090, per hour)

| Provider | Tier | $/hr | Model |
|----------|------|------|-------|
| Vast.ai | Marketplace spot | $0.16–$0.31 | Peer-to-peer, host-dependent |
| RunPod | Community Cloud | $0.34 | Fixed, no SLA |
| TensorDock | Spot | $0.44 | Less well-known |
| Jarvis Labs | On-demand | $0.49 | Fixed, India/EU regions |
| RunPod | Secure Cloud | $0.69 | Fixed, with SLA |

## Storage Costs

| Provider | Type | Cost/GB/mo | Notes |
|----------|------|-----------|-------|
| RunPod | Container disk | $0.10 | Ephemeral, lost on stop/restart |
| RunPod | Volume disk | $0.10 ($0.20 stopped) | Survives stop, lost on pod delete |
| RunPod | Network volume (Standard) | $0.07 (<1TB), $0.05 (>1TB) | Truly persistent, **Secure Cloud only** |
| Jarvis Labs | File storage | $0.10 | Persistent, max 2TB |
| Vast.ai | Container storage | $0.05–$0.10 (varies) | Host-set rates, charged continuously |
| Hugging Face Hub | Model/dataset repos | **Free** | Public & private repos, free egress |

## Total Cost Scenarios (RTX 4090, 100 hrs/mo GPU + storage)

| Setup | GPU | 500GB storage | **Total/mo** |
|-------|-----|---------------|-------------|
| Vast.ai (cheapest GPU + ~$0.07/GB) | $25 | ~$35 | ~$60 |
| RunPod Community + network volume (but NV not avail on Community) | — | — | N/A |
| RunPod Community + container disk ($0.10/GB) | $34 | $50 | $84 |
| RunPod Secure + network vol ($0.07/GB) — note NV is Secure-only | $69 | $35 | $104 |
| Jarvis Labs + file storage ($0.10/GB) | $49 | $50 | $99 |

## Storage Architecture by Provider

### RunPod
- **Community Cloud**: container disk only OR volume disk. NO network volumes.
- **Secure Cloud**: all three types (container, volume, network volume).
- Network volume replaces the pod's `/workspace` entirely.
- Container disk costs continue at $0.10/GB/mo even when pod is running.

### Jarvis Labs
- Ephemeral `/home` storage included in GPU price.
- Persistent file storage (`/home/jl_fs`) billed at $0.10/GB/mo provisioned (not usage).
- Supports "Paused" state — compute stops, storage continues.
- File storage is NFS-backed distributed filesystem, max 2TB.

### Vast.ai
- Container disk size set at creation, cannot be resized later.
- Volumes are local-only (tied to physical machine, cannot migrate).
- Storage pricing set per-host — varies significantly.
- Storage charges apply even when instance is stopped.

## Weight Storage Loop (cost-avoidance pattern)

Use **Hugging Face Hub** as the permanent home for trained weights:
1. Train on RunPod/Vast/Jarvis (ephemeral/persistent storage for active work)
2. Push final weights to HF Hub via `huggingface_hub.upload_folder()` or `huggingface-cli upload`
3. Destroy instance — no ongoing storage costs for model artifacts
4. Next session: `snapshot_download()` to pull weights back

HF Hub pros: free storage, free egress, versioned, public/private repos, streaming dataset support.

## Sources (July 2026)
- GridStackHub live RTX 4090 pricing: https://gridstackhub.ai/providers/runpod-rtx4090
- RunPod pricing page: https://www.runpod.io/pricing
- RunPod storage docs: https://docs.runpod.io/pods/storage/types
- Jarvis Labs pricing: https://jarvislabs.ai/pricing
- Jarvis Labs storage docs: https://docs.jarvislabs.ai/filestorage/
- Vast.ai pricing docs: https://docs.vast.ai/guides/instances/pricing
- Vast.ai storage docs: https://docs.vast.ai/guides/instances/storage/types
- HF Hub download guide: https://huggingface.co/docs/huggingface_hub/guides/download
