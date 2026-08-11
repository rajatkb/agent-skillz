---
name: planning-mode
description: Use create_plan to decompose complex goals into structured tool-call plans via Gemma4 on NPU, then have DeepSeek review, approve, and execute
tags: [planning, gemma-npu, create_plan, decomposition, deepseek]
category: ml-agents
---

# Planning Mode — Decompose Goals with Gemma4, Execute with DeepSeek

## Trigger

Use this workflow on **any moderately complex task** — 3+ steps, branching decisions, or tasks where upfront decomposition would help avoid sequencing mistakes. The user prefers aggressive use: err on the side of calling `create_plan`.

Specifically good candidates:
- Multi-step research or fact-finding that spans web searches and file reads
- Debugging tasks where you need to check state, then conditionally act
- Tasks combining different tool types (terminal + web + file + NPU)
- Anything where you might miss a step if you just reason through it yourself

**Do NOT use for**: single-tool calls, direct questions the user can answer in one response, or tasks so trivial they're one terminal command.

Available anytime the `create_plan` tool is registered (via `gemma-npu` plugin on the `npu` toolset). FLM must be running.

## Value Proposition

**Gemma4 (2B) on NPU produces cheap structural decomposition (~$0.0003, ~50s) so DeepSeek doesn't burn expensive thinking tokens on "what should I do next?".**

A Gemma plan is a **cheap outline** that DeepSeek reviews in seconds, accepting ~80% of the structure as-is. Without it, DeepSeek spends the first 3-5 turns reasoning through the same decomposition — costing more in thinking tokens than the NPU round-trip.

Tradeoff: NPU time is free (your hardware), DeepSeek thinking tokens are not. Every plan Gemma gets right is pure savings.

## What a Plan Should Be (and NOT Be)

**Plan = WHAT to do, WHAT order, WHAT tools to use. NOT how to implement each step.**

Correct scope (good):
```
Step 4: "Research open-source Windows global hotkey libraries.
         web_search for: AutoHotkey RegisterHotKey alternatives Rust"
         complexity: simple, executor: npu"
```

Wrong scope (bad — pushes implementation detail onto a 2B model):
```
Step 4: "Use RegisterHotKey via windows-sys crate calling
         User32::RegisterHotKey with MOD_ALT | MOD_CONTROL..."
```

Gemma4 (2B) **cannot recall exact API signatures** — its training data may have partial crate names but never the current function signatures, version numbers, or deprecation status. Pushing for implementation detail makes it hallucinate confidently wrong APIs, which DeepSeek then has to detect and fix — negating the savings.

**Acceptance criteria for a good Gemma plan:**
1. ✅ **Correct components** — all necessary pieces identified (no missing steps)
2. ✅ **Correct ordering** — dependencies in right sequence
3. ✅ **Correct tool selection** — web_search for research, terminal for commands, self for reasoning
4. ✅ **Right scope** — not too granular (15 trivial steps) and not too coarse (2 giant steps)
5. ❌ **NOT required** — crate names, function signatures, API endpoints, exact commands

If the plan passes 1-4, accept it and fill in implementation detail during execution. That's DeepSeek's job.

## Workflow

### 1. Call create_plan

Pass the goal and any relevant context:

```
goal: "the user's request"
context: "file paths, constraints, background info"
```

**Goal phrasing matters.** Be specific about what kind of output you want. For research tasks:

```
goal: "Plan the investigation: what to search for, in what order, 
       what questions to answer at each step"
```

Avoid pushing for implementation detail in the goal — that encourages Gemma to hallucinate. Keep it focused on decomposition.

### 2. Review the plan

DeepSeek validates each step against the acceptance criteria:
- Correct components? Any missing pieces?
- Correct ordering? Dependencies right?
- Correct tool selection?
- Right scope? Not too granular or coarse?

**Do NOT evaluate against** — crate names, function signatures, command syntax, API docs. Those are implementation details filled in during execution.

### 3. Report disposition

After review, always tell the user:
```
create_plan proposed: [X steps, Y complexity]
Disposition: [approved | approved-with-modifications | rejected]
Reason: [what was good/bad]
```

If you modified the plan during execution (added steps, reordered), say so explicitly. This lets the user evaluate create_plan's quality over time.

### What to do when steps are too vague

If a step says "Analyze the data" or "Examine the results" without specifying how:
- **Accept the structure** — the decomposition is right
- **Flesh out the vague step yourself** during execution — add the concrete search query, the specific check, the actual tool call
- Report this as "approved-with-modifications" with the reason: "Step N was vague, fleshed out during execution"

This is normal for a 2B model. The structure is the value, not the filling.

### 4. Execute approved plan

For NPU steps — call the tool and collect results.
For DeepSeek steps — use your own reasoning/tools.

Handle inter-step dependencies (depends_on). Steps with no dependencies can run in parallel.

## Plan Schema

```json
{
  "plan_name": "Research Workflow",
  "summary": "Search for hotkey tools, then OCR libraries, then integration patterns",
  "steps": [
    {
      "step_id": 1,
      "description": "Search for open-source global hotkey libraries for Windows",
      "tool": "web_search",
      "expected_args": {"query": "..."},
      "complexity": "simple",
      "recommended_executor": "npu",
      "depends_on": []
    }
  ],
  "estimated_complexity": "medium",
  "reasoning": "Why this decomposition makes sense..."
}
```

## Gemma4 Planning Profile (Empirical)

Through testing (Jul 2026), Gemma4 E2B consistently:

**Good at:**
- ✅ Component identification — naming the right pieces (hotkey, OCR, LLM, overlay)
- ✅ Ordering — sensible dependency chains
- ✅ Tool selection — knows when to `web_search` vs `terminal` vs `self`
- ✅ Step count — typically 4-7 steps, right granularity

**Bad at:**
- ❌ Specific search queries — terms are too broad, need sharpening during execution
- ❌ Concrete sources — never suggests looking at specific repos, docs, or APIs
- ❌ Edge-case steps — always misses 1-2 components (error handling, verification, fallbacks)
- ❌ API recall — hallucinates crate names, function signatures, version numbers
- ❌ Complexity classification — sometimes marks simple steps as complex and vice versa

This profile means: **accept the structure, sharpen the queries, add the missing steps.** The cheap outline is the value.

## Correction Pass (When the First Plan is Wrong)

If the plan is rejected, call `create_plan` again with:
- `previous_plan` = the JSON string
- `correction` = specific structural feedback

Corrections should focus on structure, not detail:

Good corrections (structure):
```
"Step 2 is missing — need to search for OCR tools before step 3"
"Step 4 depends on step 2, not step 3 — fix the dependency chain"
"Step 5 uses web_search but should use terminal"
```

Bad corrections (implementation detail — Gemma can't fix these reliably):
```
"Step 3 should use tokio_tungstenite::connect_async not tungstenite::connect"
```

The correction pass is a technique for fixing **structural** problems. For detail gaps, just fill them in during execution.

**Empirical note (Jul 2026 testing):** The correction pass reliably fixes crate names and architecture (e.g., hallucinated `glazewm_api` → corrected to `tokio_tungstenite` + `tray-icon`), but still produces vague function-level descriptions. It does NOT produce actual API signatures — that requires seeding the context with real docs.

## Chub Integration — Seeding Real API Signatures in Context

Gemma4 E2B does not know current API signatures (see empirical profile below). For tasks involving external web APIs (Stripe, OpenAI, GitHub, AWS, Discord, etc.), **seed the context with real docs before planning** using the `context-hub-api-docs` skill (requires `chub` CLI installed).

### Workflow

1. **Before calling `create_plan`**, run `chub search <api>` and `chub get <api-id> --lang <lang>` to fetch current, versioned docs
2. **Extract the real function signatures** — constructor calls, key method signatures, auth patterns, version info
3. **Include them in the `context` parameter** of `create_plan`

### Example

```
# Step 1: Fetch docs
chub get pygithub/package --lang py

# Step 2: Extract into context string:
context = "
PyGithub 2.6.0 real API:
  from github import Auth, Github
  auth = Auth.Token(os.environ[\"GITHUB_TOKEN\"])
  gh = Github(auth=auth)       # context manager pattern
  gh.get_repo(\"owner/repo\")    # returns Repository
  repo.get_issues(state=\"open\")  # auto-paginated PaginatedList
  repo.create_issue(title, body) # returns Issue
"
```

### Effect on plan quality

Without chub: "Authenticate with GitHub"
With chub: `Auth.Token(os.environ["GITHUB_TOKEN"])` + context manager pattern in step description.

The plan still doesn't produce implementation code (DeepSeek's job), but step descriptions reference **correct API objects and methods** — the structure is actionable.

### Domain match matters for few-shot

If including a few-shot example in `context`, keep the domain the same as the target task. A Python monitoring script example will anchor Gemma to Python patterns even when the target is Rust — it copies the structure but forgets domain-specific details (WebSocket, Win32, etc.).

## User Preferences (this user)

- **Aggressive trigger**: use create_plan on any moderately complex task, not just big multi-step ones. Don't default to doing it yourself — let Gemma propose, then you review.
- **Always report disposition**: after every create_plan call, tell the user whether you approved, modified, or rejected it and why.
- **Plans are about structure, not implementation**: never push for crate names, API signatures, or command syntax in the plan. That's DeepSeek's job during execution.
- **Use NPU for cheap decomposition, DeepSeek for expensive execution**: Gemma4 on NPU produces the outline (~$0.0003, ~50s); DeepSeek fills in implementation detail during execution. This is the core value proposition — don't expect Gemma to produce executable code.
- **Separate research from planning**: if the task involves unknown APIs, search/fetch docs first (via chub or web_search), then plan with the real signatures in context. Don't ask Gemma to guess APIs.

## Pitfalls

- FLM must be running before calling `create_plan` — the tool sends to Gemma4 on NPU
- First call can be slow (~50-80s); revision calls with `previous_plan` + `correction` are faster
- Keep the `goal` concise but specific to the **structural** aspects — don't push for detail
- Don't expect Gemma to know current API versions or crate signatures — it's a 2B model
- If steps are vague ("Analyze", "Examine"), fill them in during execution — the structure is still valuable
- **Don't use for trivial tasks** — single-tool calls, direct answer questions, one-command terminal executions
- **Don't skip the disposition report** — the user explicitly asked to evaluate create_plan's quality

## Verification

Check the plan was parsed correctly:
```python
plan = data["plan"]
len(plan.get("steps", []))  # step count
```
