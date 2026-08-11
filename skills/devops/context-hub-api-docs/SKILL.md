---
name: context-hub-api-docs
title: Context Hub API Documentation
description: Use Andrew Ng's Context Hub (chub CLI) to fetch current, versioned API documentation for external services, SDKs, and libraries. Avoids hallucinating outdated API parameters from training data.
---

# Context Hub (chub) — API Documentation Integration

## Trigger

- Planning a task that involves **any external API, SDK, or library** — web APIs (Stripe, OpenAI, GitHub, Discord, etc.), cloud providers (AWS, GCP, Azure), or any package/service with a public API.
- An agent needs to confirm the **current parameters, endpoints, or versions** of an API before writing code or making calls.
- `create_plan` produces a step that references an API — fetch docs first so the plan includes real function signatures instead of guesses.

## How to use

Install: `npm install -g @aisuite/chub` (already installed on this system).

### Search for docs

```bash
chub search <query>
```

Examples:
```
chub search stripe
chub search openai
chub search discord
chub search "aws s3"
chub search github api
```

Returns a list of matching doc entries with IDs, language tags, and source trust levels (`official`, `maintainer`, `community`).

### Fetch docs

```bash
chub get <id>              # basic doc
chub get <id> --lang py    # Python-specific variant
chub get <id> --lang js    # JavaScript-specific variant
chub get <id> --file <ref> # fetch a specific reference file only (minimal tokens)
chub get <id> --full       # fetch everything (multiple reference files)
```

Examples:
```
chub get openai/responses
chub get stripe/api --lang py
```

### Annotate docs (persist knowledge across sessions)

```bash
chub annotate <id> "Your note about a workaround or behavior"
chub annotate <id> --clear           # remove annotations
chub annotate --list                 # list all local annotations
chub get <id> --with-annotations    # fetch doc + annotations together
```

Use this when you discover a non-obvious behavior or workaround — the note persists and will be included in future fetches. Annotations are treated as untrusted input by default (opt-in via `--with-annotations`).

### Rate docs (improves the registry)

```bash
chub feedback <id> up
chub feedback <id> down
```

## When to use in planning flow

1. **Before calling `create_plan`**: if the task involves known APIs, run `chub search <api>` first. If docs exist, include the real function signatures in the `context` parameter so Gemma 4 can reference them accurately.

2. **During execution of code steps**: if a step requires calling an API, run `chub get <id>` to get current docs before writing code. This avoids using deprecated parameters or missing newer endpoints.

3. **After discovering a workaround**: use `chub annotate` to save it locally so the knowledge persists across sessions.

## Limitations

- Registry is **web-API focused** — strong coverage of OpenAI, Stripe, AWS, Auth0, Airflow, ChromaDB, and similar SaaS APIs. Limited coverage of Rust crates, Win32 APIs, PowerShell, or niche libraries.
- Community-contributed — quality varies by entry. Check the `source` field: `official` > `maintainer` > `community`.
- CLI-only — agents need shell access. No MCP server as of Jul 2026.
- 622 entries and growing (as of Jun 2026). If something is missing, contribute via PR to [github.com/andrewyng/context-hub](https://github.com/andrewyng/context-hub).

## Related

- Use `create_plan` with API doc context for decomposing doc-heavy tasks
- `references/tested-apis.md` — coverage map of what queries return results vs miss on this system
