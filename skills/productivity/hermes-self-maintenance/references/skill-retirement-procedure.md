# Skill Retirement Procedure (dependency-safe removal)

How to remove or slim skills and references without breaking the rest of the library.
**USER PREFERENCE (Aug 2026): user-requested removals are DELETES — `rm -rf`, never
`.archive/`.** The user rejected the archive pattern outright ("just delete, don't keep
in archive") and later hard-deleted the `amd-npu-stale-refs` archive group itself.
`.archive/` remains only for the curator's automatic transitions. Before deleting, take
a snapshot: `hermes curator backup` → `skills/.curator_backups/<ts>`; restore via
`hermes curator rollback`.

## Usage telemetry (find the unused ones — evidence, not vibes)

```bash
hermes curator usage   # per-skill: use / view / patch / act counts + last_activity
```

Cold = 0–1 `use` AND stale (weeks). Cross-check borderline skills against what the user
actually does before cutting. Duplicates with an active survivor (Playnite cluster:
5 theme skills → 2 active) are prime candidates.

## 1. Inventory first

```bash
find ~/.hermes/skills -name "*.md" -type f -printf "%TY-%Tm-%Td %10s  %p\n" | sort -r
```

- Dates reveal staleness: Jul 4–11 snapshots superseded by an Aug 7 catalog, E4B-era docs
  pre-dating the e2b default switch, etc.
- Skip: vendored trees (`lsp/node_modules/`), `memories/`, `logs/curator/`. `crawl_sessions/`
  are research deliverables the user reads — but in the Aug 2026 full trim the user chose
  to delete them (2 stale sessions, 445KB). Offer them as an option; delete only with the
  user's explicit pick.

## 2. Map the dependency graph BEFORE moving anything

- **Symlinks into the skill dir**: `ls -la ~/.hermes/scripts/` then `readlink` on suspects.
  Example: `flm-up.sh` / `flm-down.sh` symlink into `amd-npu/scripts/` — archiving that
  skill would break the gemma-npu plugin's FLM lifecycle.
- **Cross-references**: `grep -rln "<skill-name>" --include="*.md" ~/.hermes/skills` —
  every hit must be re-pointed or confirmed unaffected (flm-lifecycle, validation-procedure,
  gemma-npu-tools all referenced amd-npu).
- **Supersession check**: before archiving a reference, verify the replacement actually
  covers it — read heads of both. Example: `flm-lifecycle/references/flm-model-catalog.md`
  (Aug 7) had absorbed model-cards / model-tags / npu-benchmarks content (tool-calling
  matrix + decode TPS) → those Jul 4–11 files were safe to archive.

## 3. Archive (reversible)

```bash
mkdir -p ~/.hermes/skills/.archive/<group>/
mv devops/<skill>/references/<file>.md .archive/<group>/
```

Group by reason for one cleanup pass (e.g. `.archive/amd-npu-stale-refs/`).

## 4. Fix pointers in what remains

- Grep the kept SKILL.md for each archived filename.
- Remove the reference-list lines; re-point "See `references/X`" to the live replacement
  (e.g. model-tags → flm-model-catalog); delete now-dangling "See" clauses inside tables.

## 5. Verify

- `grep -rn "<archived-filename>" --include="*.md" ~/.hermes/skills | grep -v .archive` → empty.
- Symlinks still resolve: `ls -la` + actually run the script (`bash flm-up.sh` → "already running").
- Kept skill still loads (skill_view returns content, frontmatter intact).

## Pitfalls

- **search_files content-search returns 0 on `~/.hermes/skills`** even for terms known to
  exist (this tree). Use terminal `grep -rin` or skill_view when auditing skills.
- **A skill edited TODAY is not stale** — check mtimes. The user actively curates
  (amd-npu SKILL.md was updated the same day as the cleanup request). When the scope is
  ambiguous (slim vs archive-whole), present the audit and let the user choose — they
  picked "slim" here.
- **Keep references that hold unique knowledge** even if old (npu-memory-limits,
  wsl-powershell-quirks had no replacement); archive only superseded/stale ones.
- Archiving is scoped to doc artifacts: keep factual rows about still-valid things
  (e.g. the e4b model row stays in the catalog — only the dead doc pointers go) unless
  the user says otherwise.
- After the move, clean stray blank lines left by delete-style patches in the kept file.
