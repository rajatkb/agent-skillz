---
name: agent-skillz-sync
description: Sync local Hermes skills into the agent-skillz GitHub repo — updates for skills already in the repo, on-demand addition of newly created skills, with mandatory PII scrubbing (usernames, home dirs, vault/game paths → <user>/<Game> placeholders) and a leak-blocking verification gate. Never resurrects pruned skills.
triggers:
  - user says "sync skills to the repo", "check in the new skill", "update agent-skillz", "push skills to github"
  - after creating a new skill that should be shared
  - after editing an existing skill locally
  - user asks to verify the repo is in sync with local skills
category: productivity
---

# Agent Skillz Sync

One-way, curated, PII-scrubbed sync: **local `~/.hermes/skills` → `~/Work/agent-skillz`**.
The repo is the public face (scrubbed, curated); local keeps real paths (they are
needed to function). This skill is the discipline that keeps the two consistent.

## The rule of the repo (context)

- The repo only contains skills worth sharing — pruned one-offs are **never** resurrected.
- Repo copies are scrubbed (`<user>`, `<username>`, `<Game>`, `<email>` placeholders).
- Local copies keep real paths. Only repo copies get scrubbed.
- Runtime state (`data.json`, `sessions.json`, `*.log`, `.usage.json*`, `__pycache__`)
  never ships.

## Quickstart

```bash
# 1. Dry-run: see what would change (updates vs new vs pruned) — always first
bash ~/.hermes/skills/productivity/agent-skillz-sync/scripts/sync_skillz.sh

# 2. Apply updates to skills already in the repo
bash .../sync_skillz.sh --apply

# 3. Add a NEWLY created skill (never --include-new blindly — review the list first)
bash .../sync_skillz.sh --apply productivity/my-new-skill
```

## Semantics (what the script does)

| State | Meaning | Sync behavior |
|---|---|---|
| **updated** | skill exists locally AND in repo | copy + scrub, overwrites repo copy |
| **new** | skill exists locally, NOT in repo | listed for review; added only via explicit `<cat>/<skill>` arg or `--include-new` |
| **pruned** | in repo, NOT local | **never touched** — script never runs `rsync --delete` |

New skills get a review gate on purpose: the pruned set (~30 skills) still exists
locally, so an unguarded "sync everything" would resurrect exactly the noise we
cut. Only add skills that meet the gold-standard bar (used repeatedly, or a
durable playbook for a recurring class — research/debugging/crawling/tweaks/automation).

## The scrub map (applied to repo copies only)

| Find | Replace with |
|---|---|
| `rajat-g14` | `<user>` |
| `RAJAT` | `<user>` |
| `rajatkb.github.io` | `<username>.github.io` |
| `rajatkb` (bare, e.g. `rajatkb/<username>.github.io`) | `<username>` |
| `rajatthepagal` | `<email>` |
| known real game roots (e.g. `/mnt/d/Halo.Campaign.Evolved...`) | `/mnt/d/<Game>` (specific entries in the script's map) |

Unknown real paths (e.g. a new game root) trip the script's **warning pass**:
it scans for `/mnt/<drive>/<Capitalized>` paths (excluding known generics) and
lists them for manual review — the agent scrubs those by hand before commit.

Code that hardcodes user paths should be made **portable**, not masked:
`USERPROFILE` env var (WSL inherits it), `Path.home()`, or `~` — see
`dlss_manager.py` and `analyze_flips.py` in the repo for the established pattern.
PITFALL: `os.path.join("/mnt/c", "/Users/...")` silently drops `/mnt/c` on POSIX —
use string concatenation. Fallback strings must include the drive prefix
(`r"C:\Users\Public"`, not `r"\Users\Public"` — `[2:]` strips `\U`).

## What never syncs

- `.hub/`, `.curator_backups/`, `.curator_state/`, `.usage.json*` — Hermes runtime
  caches/ledgers (`.usage.json*` is gitignored in the repo)
- `__pycache__/`, `*.pyc`
- Runtime state files (`data.json`, `sessions.json`, `last_report.txt`, `*.log*`)
- The sync skill's own dir — it documents the scrub map, so it is exempt from
  scrubbing and from the PII gate (by design; the map lives in the SKILL.md)

## After `--apply` — README upkeep (the agent does this)

1. If skills were **added**: insert a row in the matching category table, bump
   `### <category> · N` counts, badge (`skills-N`), and the highlights count.
2. If skills were **removed** (pruned): the same in reverse (use `git log` to
   restore the README diff pattern from a prior prune commit).
3. Verify the badge count: `find skills -name SKILL.md | wc -l` (active + archived).
4. Commit with a message following the repo convention, e.g.
   `chore(sync): update <skill> — <what changed>` or `feat: add <skill> skill`.

## Verification gate (run before every commit)

```bash
cd ~/Work/agent-skillz
# must print nothing (the sync skill's own dir is exempt by design)
find skills -type f -not -path '*/agent-skillz-sync/*' \
  -exec grep -liE 'rajat-g14|RAJAT|rajatthepagal' {} + 2>/dev/null || true
# game/folder leaks:
git grep -nE '/mnt/[a-z]/[A-Z][A-Za-z0-9._-]+' -- skills/ | grep -v '<Game>\|SomeGame\|/mnt/[a-z]/foo'
```

Also check `git status` before pushing: the diff should contain **only** the
intended skill changes — never `.usage.json*`, logs, or unrelated files.

## Pitfalls

- **NEVER** run `rsync --delete` from local → repo. It deletes pruned skills.
- **NEVER** commit an unscrubbed copy. Local files have real paths — the repo
  must not. The leak gate exists for exactly this; if it trips, stop and scrub,
  don't force.
- **History is not scrubbed.** `git filter-repo` / squash was NOT yet run on the
  repo's early commits (they contain un-scrubbed paths). New commits from this
  skill are clean; the pre-existing history is the known caveat until rewritten.
- A re-sync after a local edit re-introduces real paths — that's expected; the
  copy+scrub step is what fixes them. Always scrub after copy, in that order.
- Binary detection: `file` is NOT installed on this box, and bash `$'\x00'` is an
  empty string (bash can't hold NUL) — the script uses python3 for the NUL check;
  don't "simplify" it back to either of those.
- The update rsync re-copies files deleted from the repo but still in local
  (e.g. a pruned reference). After `--apply`, check `git status` and
  `git clean -fd` the strays — the script warns about this.
- Local category dirs include pruned skills — treat the dry-run "new" list as a
  review queue, not an action list.
