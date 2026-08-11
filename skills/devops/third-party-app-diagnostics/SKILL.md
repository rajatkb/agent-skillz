---
name: third-party-app-diagnostics
description: Diagnose third-party app behavior — memory/resource usage, missing settings, hidden features — by reading the source of the EXACT release the user runs. Branch/version-aware; verify features against the user's actual release, never the default branch alone. Use when a user asks why an app behaves oddly, eats RAM, buffers whole files, or when a setting you expect isn't visible in their version.
---

# Third-Party App Diagnostics

Investigate why an app does X by reading its real source, pinned to what the user actually runs. The #1 failure mode is diagnosing against the wrong branch/version and asserting a feature exists that the user's release never shipped.

## When to use
- "Why does app X keep N GB in memory / buffer the whole file / use so much RAM?"
- "I can't find setting Y" / "that feature isn't visible in my version"
- "What is this file/folder on my drive, can I delete it?" — mystery hidden files → attribute to the app that created them, then judge safe-to-delete.
- Any behavioral claim about a third-party app that needs verification from source.

## Workflow
1. **Disambiguate the app first.** Common names collide (e.g. "Harbor" = harborstremio/harbor, a Stremio client — not the Docker registry, not a media server). Confirm from the user's description (streaming HDR 4K → media player context) before searching.
2. **Pin the user's version.** GitHub releases API: `curl -s https://api.github.com/repos/<owner>/<repo>/releases?per_page=15` → tag, published date, prerelease flag. If ambiguous, ask for the version (Settings → About/Advanced) BEFORE deep-diving.
3. **Map release → branch/tag.** Many projects ship beta far ahead of stable (Harbor's `beta-branch` has features `main` never shipped). Diff file-by-file across branches: `curl -s https://raw.githubusercontent.com/<owner>/<repo>/<branch>/<path>`.
4. **Verify UI claims in the user's branch.** Grep THAT branch's settings/UI views AND its defaults file for the toggle. A config key in `defaults.ts` with no UI wiring and no effect is dead code — do not claim it exists.
5. **Walk the pipeline layer by layer.** Player (cache config), downloader/torrent engine, HTTP proxy (does it stream or buffer?), UI webview. Read the config values the app actually sets at each layer.
6. **Verify dependencies at the exact pinned version.** Read the version from `Cargo.toml`/`package.json`, then fetch the exact published crate: `curl -sL https://static.crates.io/crates/<name>/<name>-<ver>.crate | tar xz` — the tarball is ground truth (docs.rs source pages are HTML-wrapped; GitHub tags may 404). Pay special attention to DEFAULTS of options the app does not set — defaults decide the behavior.
7. **Memory complaints: separate app RAM from OS page cache.** Task Manager "In use" (working set) vs "Cached"/standby. Media pipelines have layered caches: mpv `--cache` stream cache goes to disk with `cache-on-disk=yes` + `cache-dir`; the demuxer cache (`demuxer-max-bytes`, `demuxer-readahead-secs`) is ALWAYS RAM. If app-side is bounded but usage scales with file size, it's almost always page cache — say so, and say what the app does NOT do (bounded values) so the user can compare.
8. **Ask targeted diagnostics before concluding.** Version, which process is big, "In use" vs "Cached", and the mode (debrid vs P2P) pin down the layer in one round-trip. Don't guess when the answer forks on these facts.

## Mystery hidden files on a drive root ("what are these, can I delete them?")
1. **List the drive root with hidden files**: `ls -la /mnt/<drive>/` from WSL.
2. **Read the file before judging by name.** Tiny files (bytes) are usually app markers, not junk. Dump them: `od -c <file>` (or `xxd` if installed). UTF-16LE strings decode cleanly with od; magic bytes + a readable string identify the creator.
3. **Attribute via content + config, not vibes.** Examples that actually occurred on the user's F: drive:
   - `.GamingRoot` (18 B) = `RGBX\x01\x00\x00\x00` + UTF-16LE `"xbox"` → Xbox app install-drive marker. Harmless, self-regenerating; deleting it can break Xbox app drive detection (documented fix = copy the file back). Leave it.
   - `.<40-hex>.parts` (MBs) = orphaned partial download fragments, hash-named temp files (qBittorrent appends `.parts` to incomplete files; SavePathHistory in qBittorrent.ini proving `F:\` was a download target confirms attribution). Stale mtime + no process writing them → safe to delete.
4. **Verify attribution with a targeted web search** (`"<filename>" xbox`, `"<filename>" "safe to delete"`). These markers are widely documented; the user demands sources cited, so always land on a cited verdict (HowToGeek/SuperUser/Reddit).
5. **Verdict pattern**: marker files (bytes) → leave alone or delete-only-if-app-uninstalled; `.parts`/temp fragments (MBs, stale) → safe to delete.

## Pitfalls
- **Default branch ≠ user's release.** Never claim a UI toggle exists without finding it in that branch's settings code. If the user pushes back ("I can't see that setting"), re-verify against their branch and correct fast — don't defend.
- **Squashed history** (e.g. "beta sync" commits): `git log -S` is useless. Use the GitHub API `commits?path=<file>&sha=<branch>` endpoint to date features.
- **docs.rs source pages are HTML**; parse the crate tarball instead (see step 6).
- **librqbit API churn**: `write: bool` and `disk_cache` existed in old versions but NOT in 8.1.1 (disk storage is default via `storage_factory: None`; RAM buffering only via `defer_writes_up_to`). Verify per version — never trust remembered API shape.
- **`let _ = mpv.set_property(...)` swallows errors.** A rejected option silently falls back (e.g. cache stays in RAM if `cache-on-disk` unsupported). Check the bundled player build actually supports the option (build date/version in the app's fetch script) before trusting a config line.
- **Grep the release notes** for behavior-defining changes ("downloads the whole file to disk", "cache patch") — they document intent and versions.

## Verification
- Every claim carries a file path + line number in the user's branch, or a release-notes quote.
- End by stating the bounded values explicitly so the user can distinguish app RAM from OS cache.

## Support files
- `references/harbor-streaming-memory.md` — Harbor (Stremio client) case study: beta-vs-stable cache configs, librqbit 8.1.1 facts, mpv cache semantics, page-cache conclusion pattern.
- `references/drive-root-mystery-files.md` — drive-root forensics case study: `.GamingRoot` (Xbox app marker) and hash-named `.parts` (qBittorrent orphaned partials), decode commands, verdict pattern, sources.
