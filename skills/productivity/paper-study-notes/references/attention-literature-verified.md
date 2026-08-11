# Attention Literature — Verified References & Teaching Facts

Verified Aug 2026 while studying Serret, *Understanding Transformers and Attention Mechanisms* (arXiv 2604.00965v1 [math.NA], 1 Apr 2026, 13pp — IPAM RNLA workshop intro; author: Michel Fabrice Serret, Paul Scherrer Institute). Reuse these IDs/facts instead of re-verifying.

## Serret's references (as cited in the paper)
- **[Vas+17] Attention is All You Need** — NeurIPS 2017. MHA defined §3.2.2: "linearly project the queries, keys and values h times with different, learned linear projections". Heads do NOT split the input — the "split into heads" in diagrams/code is a reshape of the OUTPUT columns of one big `X W_Q` matmul; the input is never partitioned.
- **[BKH16] Layer Normalization** — arXiv 1607.06450. $\tilde{x} = (x-\mu)/\sqrt{\sigma^2+\epsilon}$, then $y = \gamma \odot \tilde{x} + \beta$.
- **[ZS19] RMS Layer Normalization** — NeurIPS 2019 (Zhang & Sennrich). Rescale only by RMS norm; no recentering, no bias.
- **[Xio+20] On Layer Normalization in the Transformer Architecture** — ICML 2020. Pre-LN variant.
- **[Kim+25] Peri-LN: Revisiting Normalization Layer in the Transformer Architecture** — ICML 2025, arXiv 2502.02732 (authors incl. Jeonghoon Kim, Kang Min Yoo). Third LN strategy: norm placed *around* each sublayer (pre AND post) + input/output embedding norms. Findings: balanced activation-variance growth, steadier gradient flow, convergence stability (tested up to 3.2B params). **Adopters NAMED in the paper: Gemma 2, Gemma 3, OLMo 2 — NOT Kimi.** The "Kimi" association is a conflation (citation key "[Kim+25]" reads like the model name).
- **[Sha20] GLU Variants Improve Transformer** — arXiv 2002.05202.
- **[Dee+24] DeepSeek-V2** — arXiv 2405.04434. MLA source: 60 layers, 128 heads, $d_{in}=5120$, latent $d_L=512$, MoE. Latent trained directly (not factored from K/V).
- **[Su+23] RoFormer / RoPE** — arXiv 2104.09864. Position-dependent $R_m$ applied after K is built → breaks MLA's weight merges.
- **[MYZ25] TransMLA** — arXiv 2502.07864. Converts pretrained GQA/MHA → MLA.
- **[Han+25] Streaming Attention Approximation via Discrepancy Theory** — arXiv 2502.07861.
- **[The25] Gemma 3 Technical Report** — arXiv 2503.19786. Note: its architecture change is interleaved local/global attention (KV-cache reduction), separate from the peri-LN point.
- **[Zha+24] Dive into Deep Learning** — textbook (attention-as-database analogy).

## Supplementary origin papers (NOT cited by Serret — add when the user asks for sources)
- **MQA**: Shazeer, "Fast Transformer Decoding: One Write-Head is All You Need", arXiv 1911.02150.
- **GQA**: Ainslie et al., "GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints", arXiv 2305.13245 (~8 KV groups ≈ MHA quality; MQA loses more).

## Teaching facts that clicked for this user (attention math)
- **GQA shares KEY/VALUE heads across query heads — queries are never shared.** Each query head keeps its own $W_Q^h$. Group size $s = N_{heads}/G$; query head $h$ uses KV head $g(h) = \lfloor (h-1)/s \rfloor + 1$.
- **The recurring misconception**: "heads split the base embedding" / "each head gets a different input". False — all heads consume the SAME full $x$; heads differ only by projection weights. Sharing $W_K$ within a group ⇒ K outputs *literally identical* (same $x$ × same matrix) ⇒ cache one copy per group: $2G d_{head}$ vs $2 N_{heads} d_{head}$ per token/layer. The cache win is EXACT, not approximate.
- **Kill the misconception with a tiny worked example, not prose**: $d_{in}=3$, $d_{head}=2$, $x=(1,2,3)$; two different $W_K$'s give different keys, one shared $W_K$ gives identical keys. The user needs the arithmetic.
- **GQA parameter win** ($W_K, W_V$: $N_{heads} \to G$ copies) is real but secondary — the point is the KV cache, which scales with sequence length.
- **MLA in one line**: cache one latent $L = X W_L$ ($d_L$) per token instead of per-head K/V; $\operatorname{rank}(W_K) \le d_L$ is the only approximation; merges $W_{LQK}^h = W_{LQQ}^h (W_{LK}^h)^T$ and $W_{LO} = \operatorname{blockdiag}(W_{LV}^h) W_O$ remove the need to materialize per-head K/V; RoPE breaks the merges (rotations sit between the factors) → DeepSeek appends a non-latent RoPE-carrying part.
- DeepSeek-V2 cache math: MHA would cache $2 \cdot 128 \cdot 128 = 32{,}768$ floats/token/layer; MLA caches $d_L = 512$ → 64× smaller.
