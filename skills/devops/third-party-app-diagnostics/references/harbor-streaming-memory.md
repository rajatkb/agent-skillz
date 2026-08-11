# Harbor (harborstremio/harbor) — "keeps whole 4K HDR file in memory" case study

Custom Stremio client. Stack: Tauri 2 (Rust shell) + React 19/WebView2, native **libmpv** player (bundled shinchiro mpv-dev builds, pinned in `scripts/fetch-mpv.mjs`, e.g. 20260610 git build), **librqbit 8.1.1** torrent engine (`src-tauri/src/torrent_engine.rs`), axum **stream proxy** for debrid (`src-tauri/src/stream_proxy.rs`). Branches: `beta-branch` (far ahead) vs `main` (stable). Stable releases tagged v0.9.x (v0.9.21 = 2026-07-11). `full_dl`-class features exist ONLY in beta.

## Symptom
Streaming HDR 4K (40-80 GB remux) → memory usage scales to file size. User cannot find the toggle claimed to cause it.

## Findings per layer (stable v0.9.21 / `main`)

**mpv (`src-tauri/src/mpv.rs`)** — NO full-download mode on stable; fixed bounded config (lines ~641-653):
- `cache=yes`, `cache-secs=300`, `cache-on-disk=yes` with `cache-dir` = `app_cache_dir/mpv-cache` → raw stream cache on DISK
- `demuxer-max-bytes=512MiB`, `demuxer-max-back-bytes=64MiB`, `demuxer-readahead-secs=300` → demuxer cache (RAM) capped ~576 MiB
- `stream-buffer-size=32MiB`; live mode uses 64MiB/16MiB caps
- Extra user options (`mpvExtraOptions` / `mpvTweaks`) are applied LAST via `apply_extra_mpv_options` (mpv.rs ~line 735) → they override everything above. UI: Settings → MPV → Advanced (mpv.conf), "These apply last, so they override every dial above."

**beta-branch only** — "Download the whole file while streaming" (Settings → Player → Play Mode, setting `torrentFullDownload`, default false; `src/views/settings/player-panel/play-mode-section.tsx` + `src/lib/settings/defaults.ts`). When ON, mpv.rs sets `demuxer-max-bytes=48GiB`, `demuxer-max-back-bytes=48GiB`, `cache-secs=100000`, `demuxer-readahead-secs=100000` → mpv pulls the entire file into RAM (demuxer cache is always RAM). Also primes full torrent download via `src/lib/torrent/full-download.ts` (fetch Range bytes=0- through the proxy). On `main` the key exists in defaults.ts but is dead config (no UI, no wiring).

**Torrent engine** — librqbit 8.1.1: pieces written to disk. `AddTorrentOptions` in 8.1.1 has NO `write` field (removed in v7/v8; disk storage via default `storage_factory: None`); `SessionOptions` has no `disk_cache`; RAM write buffering only via `defer_writes_up_to` (unset by Harbor). v0.9.15+ release notes: "downloads the whole file to disk and seeds it like a normal torrent client" — by design; engine cache dir bounded by the disk-cap setting (`EngineConfig.max_gb`, enforced by cache sweeper — cap enforcement bug fixed ~July 2026 per issue #616).

**Debrid proxy** — `forward_upstream` uses `upstream.bytes_stream()` → `Body::from_stream` (true streaming). Only HLS playlist rewriting buffers (small). Not a RAM sink.

## Conclusion pattern
File-size-scale "memory" on stable = **Windows page cache** (Task Manager "Cached"/standby): torrent writes + disk reads + mpv-cache writes all get cached by the OS; reclaimed on demand, not a leak. Diagnostic questions before concluding: exact version, which process is big (Harbor.exe vs msedgewebview2.exe), "In use" vs "Cached", debrid vs P2P.

## Reference facts
- mpv manual: `cache-on-disk` writes packet data "instead of keeping them in memory"; demuxer cache (`demuxer-max-bytes`/`demuxer-readahead-secs`) is always RAM.
- Releases timeline: v0.8.2-beta "Memory tweaks for lower-end PCs" (early builds had real leaks, issue #224 — fixed by updating past 0.9.7-0.9.8); v0.9.15 whole-file-to-disk torrent behavior; v0.9.18 "cache patch".
- librqbit source ground truth: `curl -sL https://static.crates.io/crates/librqbit/librqbit-8.1.1.crate | tar xz` (docs.rs pages are HTML; GitHub tags API 404'd).
