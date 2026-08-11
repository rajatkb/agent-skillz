# Multi-GPU & Enterprise GPU Pricing (July 2026)

Captured from GridStackHub live data and provider pricing pages on 2026-07-27.

## A100 80GB — RunPod

| Variant | Type | $/hr |
|---------|------|------|
| A100 SXM4 40GB | On-Demand | $1.00 |
| A100 80GB PCIe | On-Demand | $1.19 |
| A100 80GB PCIe | Spot | $1.19 |
| A100 SXM4 80GB | On-Demand | $1.39 |
| A100 SXM4 80GB | Spot | $1.39 |
| A100 SXM 80GB (high RAM) | On-Demand | $2.59 |

## A100 80GB — Vast.ai

| Variant | Type | $/hr |
|---------|------|------|
| A100 80GB | Spot (cheapest) | $0.39 |
| A100 80GB | Spot (marketplace avg) | $0.89 |

Note: Vast.ai prices are marketplace-set and vary. $0.39/hr is the cheapest observed.

## H100 — RunPod

| Variant | Type | $/hr |
|---------|------|------|
| H100 80GB PCIe | On-Demand | $2.89 |
| H100 SXM5 | On-Demand | $3.29 |

## Monthly totals (24/7 — 730 hrs)

| Config | $/hr total | $/month |
|--------|-----------|---------|
| 1× RTX 4090 (RunPod Community) | $0.34 | $248 |
| 1× RTX 4090 (Vast.ai spot) | $0.29 | $212 |
| 1× A100 80GB (Vast.ai spot) | $0.39 | $285 |
| 2× A100 80GB (Vast.ai spot) | $0.78 | $569 |
| 2× A100 80GB (RunPod PCIe) | $2.38 | $1,737 |
| 8× A100 80GB (Vast.ai spot) | $3.12 | $2,278 |
| 8× A100 80GB (RunPod PCIe) | $9.52 | $6,950 |
| 8× H100 SXM (RunPod) | $26.32 | $19,214 |

## Key takeaways

- Vast.ai spot is 3-4× cheaper than RunPod for A100/H100 tier
- RunPod Community Cloud only covers RTX 4090 and consumer GPUs — A100/H100 are Secure Cloud only
- No multi-GPU discount anywhere — cost is purely linear per GPU
