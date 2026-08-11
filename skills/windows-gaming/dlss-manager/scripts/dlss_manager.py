#!/usr/bin/env python3
"""
dlss_manager.py — DLSS DLL updater for a game root dir.

Usage:
  dlss_manager.py <game_root> [command] [flags]

Commands (default: update):
  discover        Scan for nvngx_dlss*.dll under game root, write DLSSManager/dlss.json
  update          Fetch latest (or --version pinned) DLSS DLLs from TechPowerUp,
                  back up originals, apply them. (default command)
  status          Show discovered/applied versions vs latest available on TechPowerUp
  undo            Restore each applied DLL from its newest backup (backups are NEVER deleted)

Flags:
  --version X.Y.Z     Pin target DLSS version instead of latest
  --components sr,fg,rr   Which components to update (default: all found)
  --mirror N          TechPowerUp server_id (default 15 = SG, closest to IN)

State:
  <game_root>/DLSSManager/
    dlss.json            state: discovered paths, versions, backups, applied, history
    backups/<dllname>/   immutable originals: <timestamp>_<origversion>.dll
    stash/               cached TechPowerUp zips (no re-download)

Requires: python3 (stdlib only), powershell.exe for version reads.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
import urllib.parse

SCRIPT_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# TechPowerUp download mechanics (verified 2026-08):
#   GET  page -> parse <hN>VERSION</hN> ... <form><input name=id value=N>
#   POST id=<version_id>&server_id=<mirror> -> 302 Location = direct zip URL
#   GET  that URL -> zip (use NO redirect-follow on the POST; re-POST gives 405)
# ---------------------------------------------------------------------------
TPU_BASE = "https://www.techpowerup.com/download/"
TPU_PAGES = {
    "nvngx_dlss.dll":  "nvidia-dlss-dll",
    "nvngx_dlssg.dll": "nvidia-dlss-3-frame-generation-dll",
    "nvngx_dlssd.dll": "nvidia-dlss-3-ray-reconstruction-dll",
}

# Directories that are clearly not live game files (repack leftovers, user
# stashes) — discovered but never updated.
STASH_DIR_NAMES = re.compile(
    r"^(bakup|backup|_crack|_original files?|original|old|stash|_extras|backups?)$",
    re.IGNORECASE,
)
MGMT_DIR = "DLSSManager"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

# DLSSTweaks (legit Nexus build, emoose). The zip extracts next to the game's
# main EXE. dxgi.dll is a wrapper that can be RENAMED to another supported name
# (dxgi/winmm/XInput have the best success rate). Only the nvngx.dll wrapping
# method needs the registry signature override — we never use that method, so
# no registry changes are made.
DLSSTWEAKS_WRAPPERS = ["dxgi.dll", "winmm.dll", "XInput1_3.dll", "XInput1_4.dll"]
DLSSTWEAKS_NEEDED = ["dxgi.dll", "dlsstweaks.ini", "DLSSTweaksConfig.exe"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def log(msg: str) -> None:
    print(msg, flush=True)


def err(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr, flush=True)


def die(msg: str) -> None:
    err(msg)
    sys.exit(1)


def version_tuple(v: str):
    """'310.7.0' or '310,2,1,0' -> (310, 7, 0)."""
    return tuple(int(x) for x in re.findall(r"\d+", v) or [0])


# ---------------------------------------------------------------------------
# HTTP via curl subprocess.
# NOTE: urllib is blocked by TechPowerUp (TLS fingerprinting -> 403); curl
# works. curl.exe exists on Win10+ and in WSL, so this runs on both sides.
# ---------------------------------------------------------------------------
def _curl(args: list[str], timeout: int) -> bytes:
    out = subprocess.run(["curl", "-sL", "-A", UA, *args],
                         capture_output=True, timeout=timeout)
    if out.returncode != 0:
        die(f"curl failed ({out.returncode}): {out.stderr.decode('utf-8', 'replace')[:300]}")
    return out.stdout


def http_get(url: str, timeout: int = 60, headers=None) -> bytes:
    return _curl([*(["-H", f"{k}: {v}"] for k, v in (headers or {}).items()), url], timeout)


def http_get_text(url: str, timeout: int = 60) -> str:
    return http_get(url, timeout).decode("utf-8", errors="replace")


def http_post_redirect(url: str, data: dict, timeout: int = 60) -> str:
    """POST form data; return the redirect Location (TPU download flow).

    Uses -w %{redirect_url} WITHOUT -L so the POST isn't replayed (TPU's file
    server returns 405 for re-POSTed requests).
    """
    body = urllib.parse.urlencode(data)
    out = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{redirect_url}", "-A", UA,
         "-X", "POST", "-d", body, url],
        capture_output=True, timeout=timeout)
    if out.returncode != 0:
        die(f"curl POST failed ({out.returncode}): {out.stderr.decode('utf-8', 'replace')[:300]}")
    loc = out.stdout.decode("utf-8", "replace").strip()
    if not loc:
        die(f"POST to {url} did not redirect (expected 302)")
    return urllib.parse.urljoin(url, loc)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def to_win_path(p: str) -> str:
    """/mnt/d/foo -> D:\\foo (for PowerShell)."""
    m = re.match(r"^/mnt/([a-zA-Z])/(.*)$", p)
    if m:
        drive = m.group(1).upper()
        rest = m.group(2).replace("/", "\\")
        return drive + ":\\" + rest
    return p


# ---------------------------------------------------------------------------
# PowerShell version reading (script-file pattern; inline -Command mangles paths)
# ---------------------------------------------------------------------------
_VER_PS1_TEMPLATE = """param([string]$Path)
try {
  $item = Get-Item -LiteralPath $Path -ErrorAction Stop
  $v = $item.VersionInfo.FileVersion
  if ($v) { Write-Output $v } else { Write-Output "0.0.0.0" }
} catch { Write-Output "0.0.0.0" }
"""

_WIN_PS1_PATH = r"C:\Users\RAJAT\AppData\Local\Temp\dlss_getver.ps1"
_WSL_PS1_PATH = "/mnt/c/Users/RAJAT/AppData/Local/Temp/dlss_getver.ps1"


def read_dll_version(dll_path: str) -> str:
    """FileVersion of a Windows DLL via PowerShell (works from WSL).

    Returns dotted form ('310.2.1.0') even though the PE resource stores
    commas — keeps output/JSON consistent.
    """
    try:
        with open(_WSL_PS1_PATH, "w", encoding="utf-8") as f:
            f.write(_VER_PS1_TEMPLATE)
    except Exception:
        pass
    win_path = to_win_path(os.path.abspath(dll_path))
    try:
        out = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", _WIN_PS1_PATH, "-Path", win_path],
            capture_output=True, text=True, timeout=60,
        )
        raw = (out.stdout or "").strip().splitlines()[-1] if out.stdout.strip() else "0.0.0.0"
    except Exception as e:
        log(f"  (version read failed for {dll_path}: {e})")
        raw = "0.0.0.0"
    return raw.replace(",", ".")


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------
def discover_dlls(root: str) -> dict:
    """Return {dllname: [rel paths...]} for nvngx_dlss*.dll under root.

    Skips the DLSSManager dir and stash dirs (bakup/backup/_crack/...).
    """
    found: dict[str, list] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        top = rel.split(os.sep)[0] if rel != "." else ""
        if top == MGMT_DIR or STASH_DIR_NAMES.match(os.path.basename(dirpath)):
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames
                       if d != MGMT_DIR and not STASH_DIR_NAMES.match(d)]
        for fn in filenames:
            if re.fullmatch(r"nvngx_dlss[gd]?\.dll", fn, re.IGNORECASE):
                found.setdefault(fn.lower(), []).append(
                    os.path.relpath(os.path.join(dirpath, fn), root))
    return found


# ---------------------------------------------------------------------------
# State (DLSSManager/dlss.json)
# ---------------------------------------------------------------------------
def state_path(root: str) -> str:
    return os.path.join(root, MGMT_DIR, "dlss.json")


def load_state(root: str) -> dict:
    p = state_path(root)
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception as e:
            log(f"  (state unreadable, starting fresh: {e})")
    return {
        "tool_version": SCRIPT_VERSION,
        "game_root": root,
        "discovered": {},
        "applied": {},
        "history": [],
    }


def save_state(root: str, state: dict) -> None:
    os.makedirs(os.path.join(root, MGMT_DIR), exist_ok=True)
    tmp = state_path(root) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, state_path(root))


def add_history(state: dict, action: str, details: dict) -> None:
    state.setdefault("history", []).append({
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        **details,
    })


# ---------------------------------------------------------------------------
# TechPowerUp: latest / pinned version lookup
# ---------------------------------------------------------------------------
def tpu_versions(dll_name: str, debug_dir: str | None = None) -> list[tuple[str, str]]:
    """[(version_str, version_id)] newest-first from the TPU page.

    Scrape-break resilience (see skill 'Scraping break' section):
      1. fetch retried up to 3x with backoff (transient 403/5xx/conn drops)
      2. if heading parser finds nothing, fall back to <title> (title always
         carries the latest version) + first form id
      3. if that also fails: dump raw HTML to debug_dir and die with a
         message pointing at the fix (the skill tells you how to update the
         regex). Never silently returns [].
    """
    slug = TPU_PAGES[dll_name]
    url = TPU_BASE + slug

    html = None
    last_err = None
    for attempt in range(1, 4):
        try:
            html = http_get_text(url)
            break
        except Exception as e:  # noqa: BLE001 — transient network/HTTP errors
            last_err = e
            log(f"  (fetch {dll_name} attempt {attempt}/3 failed: {e}; retrying...)")
            time.sleep(2 * attempt)
    if html is None:
        die(f"Could not fetch {url} after 3 attempts: {last_err}")

    # Primary parse: <hN>NVIDIA DLSS DLL X.Y.Z</hN> followed by its form id.
    pairs: list[tuple[str, str]] = []
    cur_ver: str | None = None
    for m in re.finditer(
        r'<h[1-6][^>]*>([^<]*?\d+\.\d+(?:\.\d+)?[^<]*)</h[1-6]>'
        r'|name="id" value="(\d+)"',
        html,
    ):
        if m.group(1):
            v = re.search(r"(\d+\.\d+(?:\.\d+)?)", m.group(1))
            cur_ver = v.group(1) if v else cur_ver
        elif m.group(2) and cur_ver:
            pairs.append((cur_ver, m.group(2)))

    # Fallback: <title> always contains the latest version; pair with first id.
    if not pairs:
        t = re.search(r"<title>([^<]*?(\d+\.\d+(?:\.\d+)?)[^<]*)</title>", html)
        ids = re.findall(r'name="id" value="(\d+)"', html)
        if t and ids:
            pairs = [(t.group(2), ids[0])]
            log(f"  (TPU heading parse failed for {dll_name}; used <title> fallback: "
                f"{t.group(2)})")

    if not pairs:
        dump_dir = debug_dir or tempfile.gettempdir()
        os.makedirs(dump_dir, exist_ok=True)
        dump = os.path.join(dump_dir, f"tpu_parse_fail_{dll_name}.html")
        with open(dump, "w", encoding="utf-8") as f:
            f.write(html)
        die(
            f"Could not parse versions from {url} — TechPowerUp page structure "
            f"changed. Raw HTML saved to {dump} for diagnosis.\n"
            f"FIX: update the parse regex in tpu_versions() — see the "
            f"'Scraping break' section of the dlss-manager skill. Retry after fixing."
        )
    return pairs


def resolve_target_version(dll_name: str, pinned: str | None, debug_dir: str | None = None) -> tuple[str, str]:
    """Return (version_str, version_id). pinned=None -> newest."""
    pairs = tpu_versions(dll_name, debug_dir=debug_dir)
    if pinned is None:
        return pairs[0]
    for ver, vid in pairs:
        if ver == pinned or version_tuple(ver) == version_tuple(pinned):
            return ver, vid
    avail = ", ".join(v for v, _ in pairs[:8])
    die(f"Version {pinned} not found on TechPowerUp for {dll_name} (available: {avail}, ...)")


def download_tpu_dll(dll_name: str, version_id: str, mirror: int, dest_zip: str) -> None:
    """TPU flow: POST id -> 302 Location -> GET zip. No redirect-follow on POST."""
    url = TPU_BASE + TPU_PAGES[dll_name]
    dl_url = http_post_redirect(url, {"id": version_id, "server_id": str(mirror)})
    data = http_get(dl_url, timeout=300)
    with open(dest_zip, "wb") as f:
        f.write(data)


def extract_dll_from_zip(zip_path: str, dll_name: str, dest_path: str) -> None:
    """Pull <dll_name> out of a TPU zip (name match, any folder level)."""
    with zipfile.ZipFile(zip_path) as z:
        target = next(
            (n for n in z.namelist()
             if os.path.basename(n).lower() == dll_name.lower() and not n.endswith("/")),
            None,
        )
        if target is None:
            die(f"{dll_name} not found inside {zip_path}")
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with z.open(target) as src, open(dest_path, "wb") as dst:
            shutil.copyfileobj(src, dst)


# ---------------------------------------------------------------------------
# Backup / apply / undo
# ---------------------------------------------------------------------------
def backup_dll(root: str, state: dict, dll_name: str, rel_path: str) -> str | None:
    """Copy original to DLSSManager/backups/<name>/<ts>_<ver>.dll if not present.

    Immutable: never overwrites, never deletes. Returns backup rel path or None.
    """
    src = os.path.join(root, rel_path)
    if not os.path.exists(src):
        return None
    h = sha256_file(src)
    existing = state.get("discovered", {}).get(dll_name, {}).get("backups", [])
    for b in existing:
        bp = os.path.join(root, b)
        if os.path.exists(bp) and sha256_file(bp) == h:
            return b  # already backed up this exact file
    ver = read_dll_version(src)
    bdir = os.path.join(root, MGMT_DIR, "backups", dll_name)
    os.makedirs(bdir, exist_ok=True)
    bname = f"{time.strftime('%Y%m%d_%H%M%S')}_{ver.replace('.', '_')}.dll"
    bpath = os.path.join(MGMT_DIR, "backups", dll_name, bname)
    shutil.copy2(src, os.path.join(root, bpath))
    state.setdefault("discovered", {}).setdefault(dll_name, {}) \
        .setdefault("backups", []).append(bpath)
    return bpath


def apply_update(root: str, args) -> None:
    state = load_state(root)
    discovered = discover_dlls(root)
    if not discovered:
        die(f"No nvngx_dlss*.dll found under {root}")
    log(f"Discovered: " + ", ".join(f"{k} x{len(v)}" for k, v in discovered.items()))

    # record discovery into state
    for dll_name, rels in discovered.items():
        ent = state.setdefault("discovered", {}).setdefault(dll_name, {})
        ent["paths"] = rels
        ent["versions"] = {r: read_dll_version(os.path.join(root, r)) for r in rels}

    wanted = [c for c in discovered if args.components is None or c in args.components]
    for dll_name in wanted:
        ver_str, ver_id = resolve_target_version(dll_name, args.version, args._debug_dir)
        for rel in discovered[dll_name]:
            src = os.path.join(root, rel)
            cur = state["discovered"][dll_name]["versions"][rel]
            if version_tuple(cur) >= version_tuple(ver_str):
                log(f"  {dll_name} @ {rel}: already at {cur} (target {ver_str}) — skip")
                continue

            stash = os.path.join(root, MGMT_DIR, "stash")
            os.makedirs(stash, exist_ok=True)
            zip_path = os.path.join(stash, f"{dll_name}_v{ver_str.replace('.', '_')}.zip")
            if not os.path.exists(zip_path):
                log(f"  downloading {dll_name} {ver_str} from TechPowerUp...")
                download_tpu_dll(dll_name, ver_id, args.mirror, zip_path)

            # backup original (immutable, idempotent)
            backup_rel = backup_dll(root, state, dll_name, rel)
            if backup_rel:
                log(f"  backed up -> {backup_rel}")

            # extract to a Windows-readable temp (stash dir) so PowerShell can
            # verify the version; Linux /tmp is not addressable from Windows
            os.makedirs(stash, exist_ok=True)
            tmp = os.path.join(stash, f".tmp_{dll_name}_{int(time.time())}.dll")
            extract_dll_from_zip(zip_path, dll_name, tmp)
            new_ver = read_dll_version(tmp)
            if version_tuple(new_ver)[:3] != version_tuple(ver_str)[:3]:
                log(f"  WARNING: downloaded {dll_name} reports version {new_ver}, "
                    f"expected {ver_str} — applying anyway (TPU naming is authoritative)")
            shutil.copy2(tmp, src)
            os.remove(tmp)

            state.setdefault("applied", {})[dll_name] = {
                "version": ver_str,
                "applied_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "path_rel": rel,
                "backup_rel": backup_rel,
            }
            log(f"  applied {dll_name} {cur} -> {ver_str} @ {rel}")

    add_history(state, "update", {"target_version": args.version or "latest"})
    save_state(root, state)
    log("Update complete. State: " + state_path(root))


def cmd_status(root: str, args) -> None:
    state = load_state(root)
    discovered = discover_dlls(root)
    print(f"Game root : {root}")
    print(f"State file: {state_path(root)}")
    print(f"{'DLL':<15} {'Current':<14} {'Latest':<10} Path")
    for dll_name in sorted(set(discovered) | set(state.get("applied", {}))):
        rels = discovered.get(dll_name, [])
        latest = "?"
        try:
            latest = tpu_versions(dll_name, debug_dir=args._debug_dir)[0][0]
        except SystemExit:
            raise
        except Exception:
            pass
        if rels:
            for rel in rels:
                cur = read_dll_version(os.path.join(root, rel))
                print(f"{dll_name:<15} {cur:<14} {latest:<10} {rel}")
        else:
            cur = state.get("applied", {}).get(dll_name, {}).get("version", "?")
            print(f"{dll_name:<15} {cur:<14} {latest:<10} (not found on disk)")
    applied = state.get("applied", {})
    if applied:
        print("\nApplied (per state):")
        for k, v in applied.items():
            print(f"  {k}: {v['version']} (backup: {v.get('backup_rel')})")
    tw = state.get("dlsstweaks", {})
    if tw.get("installed"):
        print(f"\nDLSSTweaks: installed (wrapper {tw.get('wrapper')}, v{tw.get('version')}, "
              f"zip: {tw.get('zip')})")
        print(f"  EXE dir: {tw.get('exe_dir')}")


def cmd_undo(root: str, args) -> None:
    state = load_state(root)
    applied = state.get("applied", {})
    if not applied:
        log("Nothing applied yet — nothing to undo.")
        return
    for dll_name in list(applied.keys()):
        info = applied[dll_name]
        backups = state.get("discovered", {}).get(dll_name, {}).get("backups", [])
        if not backups:
            log(f"  {dll_name}: no backups found, skipping")
            continue
        newest = backups[-1]  # chronological append order
        bpath = os.path.join(root, newest)
        if not os.path.exists(bpath):
            err(f"backup missing: {bpath}")
            continue
        dst = os.path.join(root, info["path_rel"]) if info.get("path_rel") else None
        if dst is None or not os.path.exists(dst):
            disc = discover_dlls(root).get(dll_name)
            if not disc:
                err(f"{dll_name}: cannot locate target path to restore into")
                continue
            dst = os.path.join(root, disc[0])
        shutil.copy2(bpath, dst)
        log(f"  restored {dll_name} <- {newest}")
        state["applied"].pop(dll_name, None)
    add_history(state, "undo", {})
    save_state(root, state)
    log("Undo complete. Backups retained under DLSSManager/backups/.")


# ---------------------------------------------------------------------------
# DLSSTweaks (legit Nexus build only)
# ---------------------------------------------------------------------------
def find_game_exe(root: str) -> str | None:
    """Best-match the game's main EXE.

    Scoring: normalized-name match vs the game folder > UE *-Win64-Shipping >
    shallower is better. Shells (extras/bonus/crash-report/DLC apps) excluded.
    """
    candidates = []

    def norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]", "", s.casefold())

    root_name = norm(os.path.basename(root.rstrip("/\\")))
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        top = rel.split(os.sep)[0] if rel != "." else ""
        if top == MGMT_DIR:
            dirnames[:] = []
            continue
        for fn in filenames:
            if not fn.lower().endswith(".exe"):
                continue
            stem = os.path.splitext(fn)[0]
            if re.search(r"(unins|uninstall|redist|setup|launcher|steam|epic|"
                         r"extras?|bonus|crashreport)", stem, re.I):
                continue
            score = 0
            if root_name and (root_name in norm(stem) or norm(stem) in root_name):
                score += 100  # exe name matches the game folder name
            if re.search(r"Win64-Shipping", stem):
                score += 60  # UE shipping exe is usually the game
            score -= rel.count(os.sep) * 5
            candidates.append((score, rel.count(os.sep), os.path.join(dirpath, fn)))
    if not candidates:
        return None
    candidates.sort(key=lambda c: (-c[0], c[1]))
    return candidates[0][2]


def validate_dlsstweaks_zip(zip_path: str) -> None:
    """Ensure the zip is the legit Nexus/emoose DLSSTweaks build.

    The impersonator bundle (DLSSTweaks/.github ver.4.0.6) lacks dxgi.dll /
    dlsstweaks.ini / DLSSTweaksConfig.exe and is rejected here.
    """
    try:
        with zipfile.ZipFile(zip_path) as z:
            names = {os.path.basename(n).lower() for n in z.namelist() if not n.endswith("/")}
    except zipfile.BadZipFile:
        die(f"Not a valid zip: {zip_path}")
    missing = [n for n in DLSSTWEAKS_NEEDED if n.lower() not in names]
    if missing:
        die(f"Not a DLSSTweaks zip (missing {', '.join(missing)}): {zip_path} — "
            f"get the real build from https://www.nexusmods.com/site/mods/550")


def tweak_zip_version(zip_path: str) -> str:
    """Best-effort version from Nexus filename, e.g. DLSSTweaks-550-0-310-5-0-...zip -> 0.310.5.0"""
    base = os.path.basename(zip_path)
    m = re.search(r"(\d+-\d+-\d+)-\d+\.zip$", base)
    if m:
        return m.group(1).replace("-", ".")
    return "unknown"


def cmd_tweak_install(root: str, args) -> None:
    if not args.tweak_zip:
        die("tweak-install needs --tweak-zip <path-to-DLSSTweaks.zip> "
            "(download from https://www.nexusmods.com/site/mods/550)")
    zip_path = os.path.abspath(os.path.expanduser(args.tweak_zip))
    if not os.path.isfile(zip_path):
        die(f"Zip not found: {zip_path}")
    validate_dlsstweaks_zip(zip_path)

    state = load_state(root)
    exe = find_game_exe(root)
    if not exe:
        die("Could not find the game's main EXE to install DLSSTweaks next to")
    exe_dir = os.path.dirname(exe)
    log(f"Game EXE: {exe}")

    # pick a wrapper name that doesn't already exist in the EXE dir (never
    # clobber a real dxgi.dll the game may ship)
    wrapper = next((w for w in DLSSTWEAKS_WRAPPERS
                    if not os.path.exists(os.path.join(exe_dir, w))), None)
    if wrapper is None:
        die("All DLSSTweaks wrapper names (dxgi/winmm/XInput1_3/XInput1_4) already "
            "exist next to the game EXE — refusing to overwrite. Move one aside.")

    # cache a copy of the zip in the game's stash for reuse
    stash = os.path.join(root, MGMT_DIR, "stash")
    os.makedirs(stash, exist_ok=True)
    cached = os.path.join(stash, os.path.basename(zip_path))
    if os.path.abspath(zip_path) != os.path.abspath(cached):
        shutil.copy2(zip_path, cached)

    with zipfile.ZipFile(zip_path) as z:
        # extract wrapper under its chosen name
        with z.open("dxgi.dll") as src, open(os.path.join(exe_dir, wrapper), "wb") as dst:
            shutil.copyfileobj(src, dst)
        log(f"  installed wrapper: {os.path.join(exe_dir, wrapper)}")
        for fn in ("dlsstweaks.ini", "DLSSTweaksConfig.exe"):
            target = os.path.join(exe_dir, fn)
            if os.path.exists(target):
                bdir = os.path.join(root, MGMT_DIR, "backups", "dlsstweaks")
                os.makedirs(bdir, exist_ok=True)
                bpath = os.path.join(bdir, f"{time.strftime('%Y%m%d_%H%M%S')}_{fn}")
                shutil.copy2(target, bpath)
                log(f"  backed up existing -> {os.path.relpath(bpath, root)}")
            with z.open(fn) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            log(f"  installed: {os.path.join(exe_dir, fn)}")

        # preserve the pristine (unmodified) installed files under the game
        # root, same backup tree as the DLL originals — recoverable even if
        # the live ini next to the EXE gets edited/broken later.
        pristine = os.path.join(root, MGMT_DIR, "backups", "dlsstweaks",
                                f"pristine_{tweak_zip_version(zip_path)}")
        os.makedirs(pristine, exist_ok=True)
        for fn in ("dxgi.dll", "dlsstweaks.ini", "DLSSTweaksConfig.exe"):
            with z.open(fn) as src, open(os.path.join(pristine, fn), "wb") as dst:
                shutil.copyfileobj(src, dst)
        log(f"  pristine originals -> {os.path.relpath(pristine, root)}")

    state["dlsstweaks"] = {
        "installed": True,
        "wrapper": wrapper,
        "version": tweak_zip_version(zip_path),
        "zip": os.path.relpath(cached, root),
        "exe_dir": exe_dir,
        "installed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    add_history(state, "tweak-install", {"wrapper": wrapper, "version": state["dlsstweaks"]["version"]})
    save_state(root, state)
    log(f"DLSSTweaks {state['dlsstweaks']['version']} applied next to the game EXE.")
    log("The default dlsstweaks.ini applies NO tweaks. Launch the game once — a "
        "dlsstweaks.log next to the EXE confirms it loaded. Then configure presets "
        "(L/M for DLSS 4.5) via DLSSTweaksConfig.exe.")


def cmd_tweak_remove(root: str, args) -> None:
    state = load_state(root)
    tw = state.get("dlsstweaks", {})
    if not tw.get("installed"):
        log("DLSSTweaks not installed per state.")
        return
    exe_dir = tw.get("exe_dir")
    if not exe_dir or not os.path.isdir(exe_dir):
        die(f"Cannot locate EXE dir from state ({exe_dir})")
    for fn in (tw.get("wrapper"), "dlsstweaks.ini", "DLSSTweaksConfig.exe"):
        if not fn:
            continue
        p = os.path.join(exe_dir, fn)
        if os.path.exists(p):
            os.remove(p)
            log(f"  removed {p}")
    state["dlsstweaks"] = {"installed": False}
    add_history(state, "tweak-remove", {})
    save_state(root, state)
    log("DLSSTweaks removed. DLSS DLLs, backups, and the cached zip untouched.")


# ---------------------------------------------------------------------------
# DLSSTweaks config profiles (tweak-config)
# ---------------------------------------------------------------------------
INI_SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")
INI_KEY_RE = re.compile(r"^\s*([^;#=][^=]*?)\s*=\s*(.*?)\s*$")

PRESET_SLOTS = {"DLAA", "UltraQuality", "UltraPerformance", "Performance", "Balanced", "Quality"}
PRESET_VALUES = {"Default", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M"}
SCALING_KEYS = {"Enable", "UltraPerformance", "Performance", "Balanced", "Quality", "UltraQuality"}
PROFILE_META = {"dll_version", "resolution", "source", "notes"}
INI_SECTION_MAP = {"presets": "DLSSPresets", "scaling": "DLSSQualityLevels", "dlss": "DLSS"}


def _format_ini_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return repr(v)
    return str(v)


def _set_ini_key(lines: list[str], section: str, key: str, value_str: str) -> tuple[list[str], bool]:
    """Set key=value in section, preserving all comments/order. Returns (lines, changed)."""
    n = len(lines)
    sec_start = None
    key_line = None
    last_key_idx = None
    i = 0
    while i < n:
        m = INI_SECTION_RE.match(lines[i])
        if m and m.group(1).strip() == section:
            sec_start = i
            j = i + 1
            while j < n and not INI_SECTION_RE.match(lines[j]):
                km = INI_KEY_RE.match(lines[j])
                if km:
                    if km.group(1).strip() == key and key_line is None:
                        key_line = j
                    last_key_idx = j
                j += 1
            break
        i += 1
    if key_line is not None:
        lines[key_line] = f"{key} = {value_str}"
        return lines, True
    if sec_start is None:
        if lines and lines[-1].strip() != "":
            lines.append("")
        lines.append(f"[{section}]")
        lines.append(f"{key} = {value_str}")
        return lines, True
    insert_at = (last_key_idx + 1) if last_key_idx is not None else (sec_start + 1)
    lines.insert(insert_at, f"{key} = {value_str}")
    return lines, True


def apply_profile_to_ini(ini_path: str, profile: dict) -> list[str]:
    """Merge profile sections into dlsstweaks.ini in place. Returns change list."""
    with open(ini_path, "r", encoding="utf-8-sig") as f:
        lines = f.read().splitlines()
    changes: list[str] = []
    for profile_key, ini_section in INI_SECTION_MAP.items():
        kv = profile.get(profile_key) or {}
        for key, val in kv.items():
            lines, _ = _set_ini_key(lines, ini_section, key, _format_ini_value(val))
            changes.append(f"{ini_section}.{key} = {_format_ini_value(val)}")
    with open(ini_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return changes


def validate_profile(profile: dict) -> None:
    """Reject malformed profiles before touching any ini."""
    if not isinstance(profile, dict):
        die("Profile must be a JSON object")
    unknown = set(profile) - PROFILE_META - set(INI_SECTION_MAP)
    if unknown:
        die(f"Unknown profile keys: {sorted(unknown)} (allowed: "
            f"{sorted(PROFILE_META | set(INI_SECTION_MAP))})")
    presets = profile.get("presets") or {}
    for slot, val in presets.items():
        if slot not in PRESET_SLOTS:
            die(f"Unknown preset slot '{slot}' (expected one of {sorted(PRESET_SLOTS)})")
        if str(val).lower() not in {v.lower() for v in PRESET_VALUES}:
            die(f"Preset '{slot}': '{val}' invalid (expected one of {sorted(PRESET_VALUES)})")
    scaling = profile.get("scaling") or {}
    for k, v in scaling.items():
        if k not in SCALING_KEYS:
            die(f"Unknown scaling key '{k}' (expected one of {sorted(SCALING_KEYS)})")
        if k == "Enable":
            if not isinstance(v, bool):
                die("scaling.Enable must be a boolean")
        elif not (isinstance(v, (int, float)) and 0 < v <= 1):
            die(f"scaling.{k} must be a ratio in (0, 1]")
    dlss = profile.get("dlss") or {}
    for k, v in dlss.items():
        if not isinstance(v, (bool, int, float, str)):
            die(f"dlss.{k}: unsupported value type {type(v).__name__}")


def cmd_tweak_config(root: str, args) -> None:
    if not args.profile:
        die("tweak-config needs --profile <file.json>")
    p = os.path.abspath(os.path.expanduser(args.profile))
    if not os.path.isfile(p):
        die(f"Profile not found: {p}")
    try:
        with open(p, "r", encoding="utf-8-sig") as f:
            profile = json.load(f)
    except Exception as e:
        die(f"Invalid profile JSON ({p}): {e}")
    validate_profile(profile)

    state = load_state(root)
    tw = state.get("dlsstweaks", {})
    if not tw.get("installed"):
        die("DLSSTweaks not installed for this game — run 'tweak-install --tweak-zip <zip>' first")
    ini = os.path.join(tw["exe_dir"], "dlsstweaks.ini")
    if not os.path.isfile(ini):
        die(f"dlsstweaks.ini not found at {ini}")

    # immutable backup of the current ini
    bdir = os.path.join(root, MGMT_DIR, "backups", "dlsstweaks")
    os.makedirs(bdir, exist_ok=True)
    bpath = os.path.join(bdir, f"{time.strftime('%Y%m%d_%H%M%S')}_dlsstweaks.ini")
    shutil.copy2(ini, bpath)
    log(f"backed up ini -> {os.path.relpath(bpath, root)}")

    changes = apply_profile_to_ini(ini, profile)
    for c in changes:
        log(f"  set {c}")

    tw["profile"] = {**profile, "applied_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                     "backup": os.path.relpath(bpath, root), "changes": changes}
    add_history(state, "tweak-config", {"profile": os.path.basename(p), "changes": changes})
    save_state(root, state)
    log(f"Profile applied to {ini}. Previous ini backed up. "
        "dlsstweaks.log next to the EXE will confirm settings load; "
        "edit live via DLSSTweaksConfig.exe if needed.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(
        description="Update a game's DLSS DLLs from TechPowerUp.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("game_root", help="Path to the game root dir (/mnt/d/... or D:\\...)")
    ap.add_argument("command", nargs="?", default="update",
                    choices=["update", "discover", "status", "undo",
                             "tweak-install", "tweak-remove", "tweak-config"])
    ap.add_argument("--version", default=None, help="Pin DLSS version (e.g. 310.7.0)")
    ap.add_argument("--components", default=None,
                    help="Comma list: sr,fg,rr (nvngx_dlss/nvngx_dlssg/nvngx_dlssd)")
    ap.add_argument("--mirror", type=int, default=15, help="TechPowerUp server_id (default 15)")
    ap.add_argument("--tweak-zip", default=None,
                    help="Path to a legit DLSSTweaks zip (Nexus mod 550) for tweak-install")
    ap.add_argument("--profile", default=None,
                    help="Path to a DLSSTweaks profile JSON for tweak-config")
    args = ap.parse_args()

    root = os.path.abspath(os.path.expanduser(args.game_root))
    if not os.path.isdir(root):
        die(f"Not a directory: {root}")
    args._debug_dir = os.path.join(root, MGMT_DIR)

    if args.components:
        args.components = {c.strip().lower() for c in args.components.split(",")}

    if args.command == "discover":
        state = load_state(root)
        discovered = discover_dlls(root)
        if not discovered:
            die(f"No nvngx_dlss*.dll found under {root}")
        for dll_name, rels in discovered.items():
            ent = state.setdefault("discovered", {}).setdefault(dll_name, {})
            ent["paths"] = rels
            ent["versions"] = {r: read_dll_version(os.path.join(root, r)) for r in rels}
        save_state(root, state)
        log("Discovery written to " + state_path(root))
        for dll_name, rels in discovered.items():
            for r in rels:
                log(f"  {dll_name}: {r} -> {state['discovered'][dll_name]['versions'][r]}")
    elif args.command == "update":
        apply_update(root, args)
    elif args.command == "status":
        cmd_status(root, args)
    elif args.command == "undo":
        cmd_undo(root, args)
    elif args.command == "tweak-install":
        cmd_tweak_install(root, args)
    elif args.command == "tweak-remove":
        cmd_tweak_remove(root, args)
    elif args.command == "tweak-config":
        cmd_tweak_config(root, args)


if __name__ == "__main__":
    main()
