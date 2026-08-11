---
name: agent-skillz-sync
description: Maintain the agent-skillz GitHub repo — sync local Hermes skills in with mandatory PII scrubbing (usernames, home dirs, vault/game paths → <user>/<Game> placeholders) and a leak-blocking verification gate; never resurrects pruned skills. Also covers plugin/script copy rules, per-plugin README standard, removal procedure, gold-standard pruning methodology, and central README regeneration.
triggers:
  - user says "sync skills to the repo", "check in the new skill", "update agent-skillz", "push skills to github"
  - after creating a new skill that should be shared
  - after editing an existing skill locally
  - user asks to add/sync/mirror/remove a plugin, skill, or script
  - user asks to prune/curate skills down to "what I actually use" (gold-standard pass)
  - user asks to open the repo for review
category: productivity
---

# Agent Skillz Sync & Repo Maintenance

One-way, curated, PII-scrubbed sync: **local `~/.hermes/skills` → `~/Work/agent-skillz`**,
plus the full set of conventions for keeping the repo a gold-standard, public-facing
harness. The repo is the public face (scrubbed, curated); local keeps real paths
(they are needed to function). This skill is the discipline that keeps the two
consistent.

## The rule of the repo (context)

- The repo only contains skills worth sharing — pruned one-offs are **never** resurrected.
- Repo targets usefulness for OTHERS: "production-grade harness, curated for reuse
  beyond one setup" — not a personal setup log. Internal Hermes feature/config docs
  (hermes-browser, hermes-tui-configuration, hermes-voice-mode) get cut.
- Repo copies are scrubbed (`<user>`, `<username>`, `<Game>`, `<email>` placeholders).
  Local copies keep real paths. Only repo copies get scrubbed.
- Runtime state (`data.json`, `sessions.json`, `*.log`, `.usage.json*`, `__pycache__`)
  never ships.

## Repo facts

- URL: `git@github.com:rajatkb/agent-skillz.git` — SSH only. `gh` CLI is NOT installed in WSL; use plain git over SSH.
- Clone: `~/Work/agent-skillz` (branch `main`)
- Git identity if repo config lacks it: `-c user.name=rajatkb -c user.email=rajatthepagal@gmail.com`
- SSH key: `~/.ssh/rajatkb_git_login` (ssh config already maps github.com)
- License: GPLv3 (already in repo — keep it)
- Open for review: `cd ~/Work/agent-skillz && zed .` — the Zed Windows CLI is
  WSL-aware and resolves `.` as a project. One command, no reasoning. Do NOT build
  `wsl://` URIs or verify via tasklist. The CLI blocks while attached — background it.

## Quickstart (skills)

```bash
# 1. Dry-run: see what would change (updates vs new vs pruned) — always first
bash ~/.hermes/skills/productivity/agent-skillz-sync/scripts/sync_skillz.sh

# 2. Apply updates to skills already in the repo
bash .../sync_skillz.sh --apply

# 3. Add a NEWLY created skill (never --include-new blindly — review the list first)
bash .../sync_skillz.sh --apply productivity/my-new-skill
```

## Sync semantics (what the script does)

| State | Meaning | Sync behavior |
|---|---|---|
| **updated** | skill exists locally AND in repo | copy + scrub, overwrites repo copy |
| **new** | skill exists locally, NOT in repo | listed for review; added only via explicit `<cat>/<skill>` arg or `--include-new` |
| **pruned** | in repo, NOT local | **never touched** — script never runs `rsync --delete` |

New skills get a review gate on purpose: the pruned set (~35 skills) still exists
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

## Copy procedure — plugins & scripts (manual)

1. **Plugins** — copy ONLY source: `plugin.yaml`, `__init__.py`, plus module files
   (`tools.py`, `schemas.py`). NEVER runtime state. Every plugin gets a README
   (standard below). No README, no merge.
2. **Scripts** — `cp` from `~/.hermes/scripts/` → `scripts/`, and from
   `/mnt/c/Users/<user>/.hermes/*.ps1` → `scripts/windows/`. Verify model names are
   env-configurable (`FLM_MODEL` etc.) and match stack defaults — models are never
   hardcoded (user rule; observed drift: `vision_gemma4.py` hardcoded `gemma4-it:e4b`
   vs FLM's `gemma4-it:e2b`). Windows `.ps1` files copy as-is (CRLF OK; don't convert).

## Removal procedure

1. **Scripts/plugins**: delete from BOTH the repo and the source (`~/.hermes/scripts/`,
   `/mnt/c/Users/<user>/.hermes/`) — the home dir is the mirror source; leaving the
   file there resurrects it on the next sync. **Skills**: repo-only by default —
   local copies STAY (live knowledge base; reversible via git history). Deleting
   locally too happens only on explicit user request.
2. Grep for dangling references before committing:
   `grep -rn "<name>" README.md skills/ scripts/` — skills frequently document
   utility scripts as their working reference.
3. Patch each reference: point the skill at the replacement capability (e.g. the
   agent tool that superseded the script), keep reusable API-format snippets, drop
   the row from README tables.
4. Mirror patched skills back into the repo, then commit + push.

### Skill pruning (gold-standard curation)

- **Objective signal, not vibes:** `~/.hermes/skills/.usage.json` holds
  `created_at` + `last_used_at` per skill. NEVER-used skills and single-use
  concluded-project skills are the removal candidates. Judge from the ledger.
- **User's call overrides the ledger:** the user may flag a skill as redundant even
  when the ledger shows same-day use (observed: `windows-software-management`).
  Don't argue — but explicitly note the recency in the report and offer the
  one-command restore (`git checkout <sha> -- <path>`).
- **Dangling cross-references:** after removal, other skills often point at the
  removed one ("see the X skill"). Repoint to the skill that actually carries the
  knowledge (e.g. `windows-debugging` for display-mode bugs) or the skill's own
  `references/`, then mirror each patched SKILL.md back to the repo.
- **README sync checklist** — the README carries live counts in FOUR places, all
  must move together: (1) badge `skills-N` = `find skills -name SKILL.md | wc -l`
  (active + archived), (2) highlights "🧠 N skills" (ACTIVE only — most easily
  missed), (3) per-category headers (`### devops · 9`), (4) table rows. If a
  category-as-skill dir vanished entirely, also drop it from the install example
  and the repo-structure tree.

## Plugin README standard (explicit user requirement)

Each plugin README must cover: **overview** · **features** · **hooks/tools table** ·
**CLI commands** · **installation** · **configuration/env vars** · **file layout**
(marking runtime-only files as "not checked in") · **privacy notes**. Read the
plugin's `__init__.py` first and document what the code actually does — never
invent commands or hooks.

## Central README conventions

Mature-project showcase: badge row (static shields.io — `plugins-N` + `skills-N`;
the `scripts-N` badge was REMOVED Aug 2026), highlights table, plugin table with
links to per-plugin READMEs, composition diagram, per-category skill index tables,
install guide, maintenance-workflow section, license. **No Scripts section** — the
skill listing is the index; scripts still ship (referenced by their companion
skills) but are not indexed. Regenerate the skill index from the real tree
(`find skills -name SKILL.md` + per-category loop) — don't hand-maintain counts.

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
git grep -nE '/mnt/[a-z]/[A-Z][A-Za-z0-9._-]+' -- skills/ | grep -v '<Game>\|SomeGame\|/Game\|/foo\|/Users\|/Windows\|/Program'
# runtime-state leak (already-committed files hide from find):
git ls-files | grep -E 'usage\.json|data\.json|\.log' || true
# README tables (zero blank lines may sit between a | line, blank, | line):
python3 -c "l=open('README.md').read().split('\n'); print(sum(1 for i in range(len(l)-2) if l[i].startswith('|') and l[i+1].strip()=='' and l[i+2].startswith('|')))"  # must print 0
```

Also run `scripts/verify-repo-clean.sh` (gitignore-pattern verification) before
staging, and check `git status` — the diff should contain **only** the intended
skill changes — never `.usage.json*`, logs, or unrelated files.

## Privacy rules (hard requirement)

- **Never commit**: `data.json`, `sessions.json`, `last_report.txt`, `*.log`/`*.log.gz`,
  chat logs, `__pycache__`, `.hub` (40M+ of index caches),
  `.curator_backups`/`.curator_state`, `skills/.usage.json*` (usage ledger + its
  `.lock` — machine state; gitignore pattern `skills/.usage.json*`).
- The repo `.gitignore` already blocks `plugins/**/data.json`,
  `plugins/**/last_report.txt`, `plugins/**/sessions.json`, `plugins/**/sessions.count`,
  `plugins/**/*.tmp`, `*.log`, `*.log.gz`. Keep those patterns intact.
- **Tracked runtime state hides in plain sight:** `git ls-files | grep -E
  'usage\.json|data\.json|\.log'` — a `.lock` sibling can remain tracked after the
  main file was untracked (observed: the initial rsync shipped both). Fix:
  `git rm --cached <path>` (local file stays), widen the gitignore pattern, verify
  `git ls-files` clean before commit.
- User cares about session privacy strongly — a leak is a serious failure, not a nit.

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
- **patch-tool quirks on README:** (a) the fuzzy matcher can report "Found 3
  matches" for a string that grep proves unique (hyphenated shields.io badge URLs)
  — confirm with `grep -c`, then use a minimal single-line `old_string`; (b) after
  a large/multi-hunk patch, RE-READ the affected region — a long `old_string` can
  span unintended sections (observed: one replace swallowed the Archive paragraph
  AND the "Getting started" header; the blank-line check does NOT catch missing
  headers).
- **README claim accuracy:** never write global cost claims like "$0 cloud cost" —
  the setup is HYBRID (DeepSeek cloud for the main model + local NPU for offload).
  Scope claims to the component ("NPU calls run on-device at $0").
- `create_plan` is NPU-backed — if it times out, FLM is down:
  `bash ~/.hermes/scripts/flm-up.sh` first, then retry.
- Skill counts: `find skills -name SKILL.md | wc -l` counts archived +
  category-as-skill dirs too; reconcile with per-category sums before quoting.
- Local category dirs include pruned skills — treat the dry-run "new" list as a
  review queue, not an action list.

## Support files

- `scripts/sync_skillz.sh` — the curated sync (dry-run/apply/add, scrub, leak gate).
- `scripts/verify-repo-clean.sh` — gitignore-pattern + index-leak verification;
  run before every commit.
