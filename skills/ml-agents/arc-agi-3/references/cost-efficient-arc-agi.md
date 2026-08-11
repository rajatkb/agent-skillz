# Cost-Efficient ARC-AGI Approaches

ARC-AGI-1 and ARC-AGI-2 are **static grid puzzles** — given input/output examples, generate the correct output for a test input. They are NOT solved with GPU training.

## The winning paradigm: LLM API-based program synthesis

All top-scoring approaches work the same way:
1. Give a frontier LLM (Claude, GPT, Grok) the task examples as prompts
2. LLM generates candidate Python functions that solve the transformation
3. Test functions against training examples
4. Iterate: keep what works, refine what doesn't

No GPU compute needed — just LLM inference API calls.

## Cost comparison per task

| Solution | Cost/task | Score (ARC-AGI-1) | LLM calls/task | Year |
|----------|-----------|-------------------|----------------|------|
| epang080516 | **~$2.56** | 77.1% | ~10 (5 per round × 2 rounds) | 2025 |
| Berman | ~$8.42 | ~80% | ~500 | 2025 |
| OpenAI o3 | ~$200 | ~87% | massive (brute force) | 2024 |
| GPT-4o-mini (budget) | ~$0.15 | lower | ~10 | 2025 |

## For small budgets (~1000 INR / ~$12 USD)

1. **Clone [github.com/epang080516/arc_agi](https://github.com/epang080516/arc_agi)** — open source, Python
2. Get an API key (xAI Grok, OpenAI, or Anthropic)
3. Use **GPT-4o-mini** at ~$0.15/task for cheap exploration
4. Run on local CPU — `python -m src.submission -v1`
5. $12 ≈ 80 tasks with GPT-4o-mini — enough to establish a baseline on the public eval set

## Key repos

- **epang080516/arc_agi** — DreamCoder-inspired library growing, LLM-assisted search. Best performance-cost ratio.
- **Jeremy Berman's solution** — Evolutionary test-time compute. Higher cost, slightly better accuracy.
- **ARC-AGI-3** (interactive turn-based) is a different benchmark — see the main `arc-agi-3` skill for that.

## References

- ARC Prize leaderboard: https://arcprize.org/leaderboard
- epang080516 writeup: https://ctpang.substack.com/p/arc-agi-2-sota-efficient-evolutionary
- Berman writeup: https://jeremyberman.substack.com/p/how-i-got-a-record-536-on-arc-agi
