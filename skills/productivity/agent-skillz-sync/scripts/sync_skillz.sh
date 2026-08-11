#!/usr/bin/env bash
# sync_skillz.sh — sync local Hermes skills → agent-skillz repo.
#
#   - updates skills already in the repo (copy + PII scrub)
#   - adds newly-created skills ON DEMAND (explicit <cat>/<skill> args or
#     --include-new; never auto-adds everything)
#   - never touches pruned skills (no rsync --delete, ever)
#   - runs a PII leak gate before reporting success
#
# Usage:
#   sync_skillz.sh                                    dry-run (default)
#   sync_skillz.sh --apply                            update existing skills
#   sync_skillz.sh --apply <cat>/<skill> ...          update + add specific skills
#   sync_skillz.sh --apply --include-new              update + add ALL new skills
#
# Env: SKILLZ_SRC  (default ~/.hermes/skills)
#      SKILLZ_REPO (default ~/Work/agent-skillz)
set -euo pipefail

SRC="${SKILLZ_SRC:-$HOME/.hermes/skills}"
REPO="${SKILLZ_REPO:-$HOME/Work/agent-skillz}"
DEST="$REPO/skills"

MODE=dry
INCLUDE_NEW=0
declare -a REQUESTED=()
for a in "$@"; do
  case "$a" in
    --apply) MODE=apply ;;
    --include-new) INCLUDE_NEW=1 ;;
    *) REQUESTED+=("$a") ;;
  esac
done

# Self-exclusion: this skill's own dir documents the scrub map, so it is
# exempt from scrubbing AND from the PII gate (its content legitimately
# contains the pattern strings).
SELF_SLUG="$(basename "$(cd "$(dirname "$0")/.." && pwd)")"

# ── PII scrub map (repo copies only; local keeps real paths) ────────────
scrub() {
  sed -i \
    -e 's/rajat-g14/<user>/g' \
    -e 's/RAJAT/<user>/g' \
    -e 's/rajatkb\.github\.io/<username>.github.io/g' \
    -e 's/rajatkb/<username>/g' \
    -e 's/rajatthepagal/<email>/g' \
    -e 's|/mnt/d/Halo\.Campaign\.Evolved\.Premium\.Edition-InsaneRamZes|/mnt/d/<Game>|g' \
    "$1"
}

# NUL byte = binary. NOTE: bash $'\x00' is an EMPTY string (bash strings
# can't hold NUL) — grep -q $'\x00' matches everything. Use python3.
is_text() { python3 -c 'import sys; sys.exit(1 if b"\x00" in open(sys.argv[1], "rb").read(65536) else 0)' "$1"; }

# rel list of skills: "cat/skill" or bare "skill" (top-level, no category)
local_skills() { (cd "$SRC"  && find . -mindepth 2 -maxdepth 3 -name SKILL.md | sed 's|^\./||; s|/SKILL\.md$||' | sort); }
repo_skills()  { (cd "$DEST" && find . -mindepth 2 -maxdepth 3 -name SKILL.md | sed 's|^\./||; s|/SKILL\.md$||' | sort); }

# ── pass 1: diff local vs repo ───────────────────────────────────────────
updated=0
declare -a new_list=() pruned_list=() add_set=()

while IFS= read -r rel; do
  [ "${rel##*/}" = "$SELF_SLUG" ] && continue
  if [ -e "$DEST/$rel" ]; then
    updated=$((updated + 1))
  else
    new_list+=("$rel")
  fi
done < <(local_skills)

while IFS= read -r rel; do
  [ -e "$SRC/$rel/SKILL.md" ] || pruned_list+=("$rel")
done < <(repo_skills)

# ── decide the add set ────────────────────────────────────────────────────
if [ "$MODE" = apply ]; then
  for entry in "${REQUESTED[@]:-}"; do
    if [ -e "$SRC/$entry/SKILL.md" ]; then
      add_set+=("$entry")
    else
      echo "WARN: '$entry' not found locally — ignoring" >&2
    fi
  done
  if [ "$INCLUDE_NEW" = 1 ]; then
    add_set=("${new_list[@]}" "${add_set[@]}")
  fi
fi

# ── report ────────────────────────────────────────────────────────────────
echo "agent-skillz sync  [$MODE]"
echo "  updated (in repo):      $updated"
echo "  new (local only):       ${#new_list[@]}   <- review queue, not action list"
for e in "${new_list[@]}"; do echo "    + $e"; done
echo "  pruned (repo only):     ${#pruned_list[@]}  (never touched by design)"
for e in "${pruned_list[@]}"; do echo "    - $e"; done
echo "  will add:               ${#add_set[@]}"
for e in "${add_set[@]}"; do echo "    + $e"; done

[ "$MODE" = dry ] && { echo "DRY-RUN — re-run with --apply to write."; exit 0; }

# ── apply: update existing skills ─────────────────────────────────────────
[ -d "$DEST" ] || { echo "FATAL: repo skills dir missing at $DEST" >&2; exit 1; }
while IFS= read -r rel; do
  [ "${rel##*/}" = "$SELF_SLUG" ] && continue
  [ -d "$DEST/$rel" ] || continue
  rsync -a --exclude '__pycache__' --exclude '*.pyc' "$SRC/$rel/" "$DEST/$rel/"
  while IFS= read -r f; do is_text "$f" && scrub "$f"; done \
    < <(find "$DEST/$rel" -type f)
done < <(local_skills)
echo "updated $updated skill(s) in $DEST"

# ── apply: add requested new skills ───────────────────────────────────────
for entry in "${add_set[@]:-}"; do
  mkdir -p "$DEST/$entry"
  rsync -a --exclude '__pycache__' --exclude '*.pyc' "$SRC/$entry/" "$DEST/$entry/"
  if [ "${entry##*/}" = "$SELF_SLUG" ]; then
    echo "added $entry (self — copied, not scrubbed)"
    continue
  fi
  while IFS= read -r f; do is_text "$f" && scrub "$f"; done \
    < <(find "$DEST/$entry" -type f)
  echo "added $entry"
done

# ── verification gate: no PII may survive in the repo copy ────────────────
leaks=$(find "$DEST" -type f -not -path "*/$SELF_SLUG/*" \
  -exec grep -liE 'rajat-g14|RAJAT|rajatthepagal' {} + 2>/dev/null || true)
if [ -n "$leaks" ]; then
  echo "PII LEAK — aborting. Files:" >&2
  echo "$leaks" >&2
  exit 1
fi

# Warning pass: possible real game/folder paths the map can't auto-scrub
gamehits=$(grep -rnoE '/mnt/[a-z]/[A-Z][A-Za-z0-9._ -]*' "$DEST" \
  --exclude-dir="$SELF_SLUG" 2>/dev/null \
  | grep -vE '<Game>|SomeGame|/Game|/foo|/Users|/Windows|/Program' || true)
if [ -n "$gamehits" ]; then
  echo "WARN: possible real game/folder paths — review and scrub manually:"
  echo "$gamehits"
fi

echo
echo "OK — PII gate passed. Next steps (agent):"
echo "  * git status — confirm ONLY intended changes"
echo "  * WARN: files deleted from the repo but still present locally get"
echo "    re-copied by the update rsync (e.g. a pruned reference file)."
echo "    Remove them with: git clean -fd <path>"
echo "  * README: bump counts if skills were added/removed"
echo "    (total SKILL.md now: $(find "$DEST" -name SKILL.md | wc -l))"
echo "  * commit + push with a descriptive message"
