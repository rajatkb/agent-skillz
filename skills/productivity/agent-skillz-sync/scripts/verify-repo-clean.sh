#!/usr/bin/env bash
# Verify the agent-skillz repo is clean of runtime state before commit.
# Usage: bash verify-repo-clean.sh [repo_dir]
# Checks: (1) runtime-state patterns are gitignored, (2) committed source
# files stay trackable, (3) index contains no runtime state, (4) a dry-run
# `git add -A` would not stage runtime state.
set -u
REPO="${1:-$HOME/Work/agent-skillz}"
cd "$REPO" || { echo "FAIL: repo dir missing: $REPO"; exit 1; }
fail=0

must_ignore=(
  "plugins/budget-tracker/data.json"
  "plugins/budget-tracker/last_report.txt"
  "plugins/flm-lifecycle/sessions.json"
  "plugins/flm-lifecycle/sessions.count"
  "plugins/gemma-npu/whatever.tmp"
  "plugins/chat-logger/chat.log"
  "logs/chat-log/session-abc.log.gz"
  "skills/devops/foo/__pycache__/__init__.pyc"
)
for f in "${must_ignore[@]}"; do
  if git check-ignore -q -- "$f"; then echo "PASS ignored   : $f"; else echo "FAIL not ignored: $f"; fail=1; fi
done

must_track=(
  "plugins/budget-tracker/__init__.py"
  "plugins/budget-tracker/plugin.yaml"
  "plugins/gemma-npu/tools.py"
  "plugins/gemma-npu/schemas.py"
  "plugins/chat-logger/__init__.py"
  "plugins/flm-lifecycle/__init__.py"
  "README.md"
)
for f in "${must_track[@]}"; do
  if git check-ignore -q -- "$f"; then echo "FAIL wrongly ignored: $f"; fail=1; else echo "PASS tracked      : $f"; fi
done

leaks=$(git ls-files | grep -E '(data\.json|sessions\.json|last_report\.txt|sessions\.count|\.log(\.gz)?$|__pycache__)' || true)
if [ -z "$leaks" ]; then echo "PASS index clean: no runtime-state files tracked"; else echo "FAIL leaked into index:"; echo "$leaks"; fail=1; fi

dry=$(git add -A --dry-run | grep -E '(data\.json|sessions\.json|last_report\.txt|\.log)' || true)
if [ -z "$dry" ]; then echo "PASS dry-run    : git add -A stages no runtime state"; else echo "FAIL dry-run would stage:"; echo "$dry"; fail=1; fi

[ $fail -eq 0 ] && echo "=== ALL CHECKS PASSED ===" || echo "=== $fail CHECK(S) FAILED ==="
exit $fail
