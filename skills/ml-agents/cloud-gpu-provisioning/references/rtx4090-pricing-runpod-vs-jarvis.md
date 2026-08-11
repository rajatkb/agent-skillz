# RTX 4090 Pricing: RunPod vs Jarvis Labs (July 2026)

Research snapshot from July 26, 2026 conversation. Source URLs:
- RunPod pricing: https://www.runpod.io/gpu-models/rtx-4090
- RunPod storage: https://docs.runpod.io/storage/network-volumes
- Jarvis Labs pricing: https://jarvislabs.ai/pricing
- Jarvis Labs storage: https://docs.jarvislabs.ai/filestorage/
- GridStackHub comparison: https://gridstackhub.ai/providers/jarvis-labs-rtx4090
- RunPod storage options: https://docs.runpod.io/pods/storage/types

## GPU compute (RTX 4090, 24GB VRAM)

| Provider | Tier | $/hr |
|----------|------|------|
| RunPod | Community Cloud | $0.34 |
| RunPod | Secure Cloud | $0.69 |
| Jarvis Labs | On-Demand | $0.49 |
| Vast.ai | Spot | ~$0.13-0.25 (variable) |

## Persistent storage (survives instance termination)

| Provider | Type | Rate | Min/Max |
|----------|------|------|---------|
| RunPod | Network volume (standard) | $0.07/GB/mo first 1 TB, $0.05/GB/mo beyond | No min listed |
| Jarvis Labs | File storage | $0.10/GB/mo ($0.00014/GB/hr) | Up to 2TB, billed on provisioned capacity |

## Total monthly cost (example: 100 hrs GPU + 100 GB persistent storage)

| Setup | GPU cost | Storage cost | Total |
|-------|----------|-------------|-------|
| RunPod Community + network volume | $34 | $7 | $41 |
| Jarvis Labs + file storage | $49 | $10 | $59 |
| RunPod Secure + network volume | $69 | $7 | $76 |

## Storage architecture notes

### RunPod
- Container disk (~50GB default): ephemeral, lost on stop/restart, $0.10/GB/mo running
- Volume disk (/workspace): survives stop/restart, deleted on pod termination, $0.10/GB/mo running, $0.20/GB/mo stopped
- Network volume: fully persistent, shareable, replaces volume disk at /workspace when attached, $0.07/GB/mo

### Jarvis Labs
- /home directory: ephemeral, included with instance
- File storage (/home/jl_fs): persistent, $0.10/GB/mo, capacity only increasable

## Data/weight storage alternatives

| Service | Use | Cost |
|---------|-----|------|
| Hugging Face Hub | Permanent weight storage, push/pull from any instance | Free (public & private repos) |
| Torbox | Fast cached torrent downloads for datasets | $3-10/mo; read-only WebDAV, no write-back |
| Local NAS/backup | Archival | One-time hardware cost |

## Key takeaways
- RunPod Community Cloud is cheapest RTX 4090 option at $0.34/hr
- RunPod network storage ($0.07/GB/mo) is 30% cheaper than Jarvis Labs ($0.10/GB/mo)
- Hugging Face Hub is the correct free solution for permanent weight storage
- Torbox is useful for dataset acquisition only — cannot replace persistent storage
