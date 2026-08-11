# mpv cache layers & Harbor's playback modes

## mpv has two separate caches
1. **Stream cache** (`--cache`, `--cache-secs`, `--cache-dir`, `--cache-on-disk`) — raw input bytes read from the network. In memory UNLESS `cache-on-disk=yes` + `cache-dir` are set → temp file on disk (append-only; file deleted at playback close; packet *metadata* stays in memory).
2. **Demuxer cache** (`--demuxer-max-bytes`, `--demuxer-max-back-bytes`, `--demuxer-readahead-secs`) — demuxed packets. ALWAYS in RAM. This is the source of big RAM usage on large files.

## Harbor's per-mode config (src-tauri/src/mpv.rs)
| Mode | cache-secs | demuxer-max-bytes | max-back-bytes | readahead-secs | stream-buffer-size |
|------|-----------|-------------------|----------------|----------------|--------------------|
| Live TV (`is_live`) | 30 | 64MiB | 16MiB | 20 | 16MiB |
| Normal stream (default) | 300 | 512MiB | 64MiB | 300 | 32MiB |
| Full download (`torrentFullDownload`) | 100000 | 48GiB | 48GiB | 100000 | 32MiB |

All modes: `cache=yes`, `cache-pause=yes` (non-live also `cache-pause-initial=no`). Non-live additionally: `cache-on-disk=yes`, `cache-dir=<app_cache>/mpv-cache`, per-URL `network-timeout`, lavf reconnect opts (`reconnect=1,reconnect_streamed=1,reconnect_on_http_error=429,reconnect_delay_max=10,reconnect_delay_total_max=60`), `demuxer-lavf-o=http_seekable=0,http_persistent=0`.

RAM math for normal mode: 512MiB demuxer + 64MiB back + 32MiB stream buffer ≈ ~600MB ceiling. Full-download mode has no practical ceiling below 48GiB → a 40-80GB 4K HDR remux holds tens of GB in RAM.

## Override mechanism (user escape hatch)
- UI: Settings → MPV → **Advanced (mpv.conf)** — `mpvExtraOptions`, one `key=value` per line, exactly like mpv.conf; also `mpvTweaks` dials. UI subtitle states: "These apply last, so they override every dial above. Restart playback to apply."
- Rust: hardcoded cache properties set first (~lines 677-713), then `apply_extra_mpv_options` (~455-478, invoked ~735) parses each line and calls `mpv.set_property` → later writes win.
- Validation: lines matching `/^[a-z0-9-]+(=.*)?$/i` accepted; risky keys flagged (scripts, load-script, input-ipc-server, input-conf, input-cmdlist, ytdl-raw-options); unparseable lines skipped silently.

## Verified source anchors (beta-branch, Aug 2026)
- mpv.rs:692-698 — full_dl vs normal cache properties (`args.full_download.unwrap_or(false)`)
- mpv.rs:677-690 — live mode properties
- mpv.rs:455-478 — apply_extra_mpv_options
- mpv.rs:735-737 — extra options applied after hardcoded block
- torrent_engine.rs:262 — SessionOptions (fastresume:true, JSON persistence, listen 16881..16931, UPnP when "full")
- torrent_engine.rs:461-485 — AddTorrentOptions (overwrite:true, paused:true, only_files, trackers spliced into magnet, peer timeouts) — `write` unset → librqbit default = disk
- torrent_engine.rs cache sweep: initial delay 60s, interval 30min, retention via engine.json `retention_hours`/`max_gb`
- stream_proxy.rs — register/forward_upstream: forwards range/accept/user-agent/referer/origin/if-* headers + session headers; copies content-type/length/range/accept-ranges/etag/last-modified/cache-control back; streams body (no whole-file buffering)
- play-mode-section.tsx:199-219 — "Download the whole file while streaming" toggle
- defaults.ts:206-209 — directTorrentStream:true, torrentFullDownload:false, keepStreamDownloadsInBackground:false
- full-download.ts — startFullDownload() primes the torrent by fetching `Range: bytes=0-` through the local proxy (forces full download; disk-side)

## Known issue history (context for user reports)
- #224 "high usage ram" — maintainer: update out of 0.9.7-0.9.8 (old leak builds); in-app memory dump via Ctrl+Shift+M
- #616 "Disk cap doesn't do anything" — cap was only enforced at startup, not while downloading; patched in beta
- #468 / #482 — torrent cache retention/disk fill; handled by cache sweep (retention_hours / max_gb)
- #939 — cap buffered native HTTP fetches at 16 MiB (metadata paths; media proxy unaffected)
