# Vault Sync: WSL → Windows (Obsidian)

## Problem

The repo lives on WSL's ext4 filesystem (`/home/...`), but Obsidian runs on Windows. `\\wsl.localhost\` isn't reliably accessible from every Windows setup, so directory junctions/symlinks across the boundary may not work.

## Solution: rsync Mirroring + Git-Diff Verification (Push-Only)

Keep `data/vault/` in the repo (git-tracked, CI-safe). Maintain a copy at `C:\Users\RAJAT\vault` for Obsidian to open. The `scripts/sync-vault.sh` script keeps them in sync with `rsync --delete`, always pushing **Repo → Windows**.

The script runs a **git diff pre-scan** first to detect every new/modified/untracked file under `data/vault/` since `HEAD`. After the rsync, it verifies each detected file landed at the destination. This catches files that rsync might miss due to WSL mount timestamp quirks.

**Script direction is always Repo → Windows.** There is no pull-from-Windows functionality. Files created/edited on the repo side (by Hermes, git pulls, or direct editing) are synced to Windows. Obsidian-side edits should be committed via git on the WSL side.

### Setup

```bash
# One-time: install rsync and inotify-tools
sudo apt-get install -y rsync inotify-tools

# Seed the Windows copy with initial vault content
cp -a data/vault/. /mnt/c/Users/RAJAT/vault/

# Open C:\Users\RAJAT\vault in Obsidian
```

### Workflow: One-Shot Push

```bash
# After adding/changing files directly in the repo:
bash scripts/sync-vault.sh          # repo → Windows push (via git-diff pre-scan + verification)
# Changes are now visible in Obsidian
```

### Workflow: Auto-Watch (Push Direction)

```bash
# Start the watcher standalone:
npm run watch          # runs sync-vault.sh --watch in background, saves PID to .vault-watch.pid

# Kill the watcher when done:
npm run blind          # kills the PID from .vault-watch.pid, cleans up
```

The `--watch` mode uses `inotifywait` (from `inotify-tools`) to monitor `data/vault/` (native WSL ext4 filesystem — inotify works reliably here) for file changes. On each change batch, it debounces 1.5s of quiet, then runs the push rsync. This is the right mode for long-running sessions where another Hermes instance or git operations add files to `data/vault/`.

### Architecture

| File | Purpose |
|------|---------|
| `scripts/sync-vault.sh` | Core sync script: one-shot push (default) or continuous push-watch (`--watch`) |
| `package.json` `"watch"` | Starts watcher in background with PID file management: `bash scripts/sync-vault.sh --watch & echo $! > .vault-watch.pid` |
| `package.json` `"blind"` | Kills the background watcher by PID: `kill $(cat .vault-watch.pid)` |

### How It Works

- **Push (default):** Runs `git diff --diff-filter=ACMRT HEAD -- data/vault/` + `git ls-files --others` to list every new/modified/untracked file. Prints the list, then `rsync -av --delete data/vault/ /mnt/c/Users/RAJAT/vault/` mirrors repo into Windows. Excludes `.obsidian/` entirely (never pushed to Windows). Verifies each detected file exists at the destination — warns if any are missing.

- **Watch (`--watch`):** Starts `inotifywait -m -r` on `data/vault/` (native WSL ext4 filesystem). On file changes (modify, create, delete, move), debounces for 1.5s of quiet, then runs the same push logic.

Both use `--delete` so renames and deletions in the source are reflected in the destination. `data/vault/.obsidian/` is excluded from all operations.

### Verifying the Watcher Is Alive

```bash
cat .vault-watch.pid && ps -p $(cat .vault-watch.pid) -o pid,stat,args
```
If alive, you'll see the PID and the command `bash scripts/sync-vault.sh --watch`. If the PID file is missing or the process doesn't exist, restart with `npm run watch`.

### Why a Running Watcher Can Seem "Broken"

The watcher is often silent when everything is in sync — the one-shot push reports only 1-2KB of metadata because files are already mirrored. This is correct. To verify it's really working:

1. **Touch-test:** `touch data/vault/some-file.md` then wait ~3s and check the Windows side — the file should appear / timestamp update.
2. **Check watcher output:** If running via a Hermes background process, `process(action='poll')` shows the full sync log with file lists and byte counts.

### Pitfalls

- **Push mode needs a git repo.** If the script is run outside the repo context (e.g. from a cron job without a working git directory), the git-diff pre-scan will fail silently. The rsync still runs, but the verification step has nothing to check against.
- **WSL mount can cache timestamps** — on rare occasions, `rsync` may think a file is unchanged when it actually changed on the Windows side. If this happens, run `touch` on the file or force-resync with `rsync -av --size-only` as a fallback. The git-diff push mode is immune to this since it works at the git layer.
- **inotify is native WSL ext4 only** — `inotifywait` works reliably on `data/vault/` because it's on the WSL ext4 filesystem. Do NOT use `--watch` to monitor `/mnt/c/...` paths (DrvFs), where inotify may miss events.
