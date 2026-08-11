# Window Rule Debugging (ignore / fullscreen)

Use when a GlazeWM window rule "isn't working": the window still gets tiled, or doesn't go fullscreen. Worked example at the bottom (2026-08-03: Playnite launched from Xbox FSE via AnyFSE appeared "half screen").

## Step 1 — Confirm the rule is on disk and valid

```bash
grep -n "window_rules" -A 30 /mnt/c/Users/RAJAT/.glzr/glazewm/config.yaml
```

`window_process` matches the exe name WITHOUT `.exe` (same as Get-Process ProcessName). Verify against the real binaries:

```bash
ls "/mnt/c/Users/RAJAT/AppData/Local/Playnite/" | grep -i exe
# Playnite.DesktopApp.exe / Playnite.FullscreenApp.exe → rule uses 'Playnite.DesktopApp' / 'Playnite.FullscreenApp'
```

## Step 2 — Confirm the running instance loaded the config

```bash
powershell.exe -NoProfile -Command "Get-Process glazewm | Select-Object Id, StartTime | Format-List"
stat -c '%y' /mnt/c/Users/RAJAT/.glzr/glazewm/config.yaml
```

StartTime > config mtime → rules are live. Older → reload (`alt+shift+r`) or restart glazewm.exe. Do NOT attempt WebSocket IPC reloads (port 6123) — raw `{"command":"wm-reload-config"}` messages returned empty replies even after a `subscribe` handshake in this environment; the hotkey/restart is the reliable, user-preferred path.

## Step 3 — Inspect the actual window (process, class, rect)

Run with the problem window open. This lists every visible window with owner process, title, WPF/Win32 class, rect, and show state:

```powershell
Add-Type @'
using System; using System.Runtime.InteropServices; using System.Text;
public class W {
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool GetWindowPlacement(IntPtr h, ref WINDOWPLACEMENT p);
  [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder sb, int max);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }
  [StructLayout(LayoutKind.Sequential)] public struct WINDOWPLACEMENT { public int length, flags, showCmd, minX, minY, maxX, maxY; public RECT normal; }
}
'@
Get-Process | Where-Object { $_.MainWindowHandle -ne 0 } | ForEach-Object {
  $sb = New-Object System.Text.StringBuilder 256
  [W]::GetClassName($_.MainWindowHandle, $sb, 256) | Out-Null
  $r = New-Object W+RECT; [W]::GetWindowRect($_.MainWindowHandle, [ref]$r) | Out-Null
  $wp = New-Object W+WINDOWPLACEMENT; $wp.length = [Runtime.InteropServices.Marshal]::SizeOf($wp)
  [W]::GetWindowPlacement($_.MainWindowHandle, [ref]$wp) | Out-Null
  "{0} | '{1}' | {2} | {3}x{4} at ({5},{6}) | showCmd={7}" -f $_.ProcessName, $_.MainWindowTitle, $sb.ToString(), ($r.R-$r.L), ($r.B-$r.T), $r.L, $r.T, $wp.showCmd
}
```

Compare the rect against monitor bounds (`Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Screen]::AllScreens`). showCmd: 1=normal, 2=minimized, 3=maximized.

## Decision tree

- **Rules are evaluated at window CREATION.** A window opened *before* the rule existed — or before GlazeWM restarted with the new config — stays managed even though the rule is correct. After adding/changing a rule, test by FULLY closing the app and relaunching; don't conclude "rule broken" from a stale window. (Worked example below: fresh launch of Playnite confirmed the ignore rule worked.)
- **Rect ≈ tiling region** (full monitor minus gaps), showCmd=1 → window is being **TILED** → the rule did NOT match → re-check the process name; the visible window may be owned by a different process than assumed (launcher wrappers, injected hosts). Also possible: rule added but instance never reloaded (Step 2).
- **Rect ≠ tiling region, arbitrary size, showCmd=1** → window is **FLOATING — the ignore rule IS working**, but the app launched windowed at its own size. The user sees "half screen" but it's the app's fault, not the rule. Fix: add `set-fullscreen` to the rule's commands.
- **showCmd=3** → natively maximized, no issue.

## Fix: force fullscreen on an ignored window

Rule commands run in order and combine:

```yaml
window_rules:
  - commands: ['ignore', 'set-fullscreen']
    match:
      - window_process: { equals: 'Playnite.FullscreenApp' }
```

Confirmed-combining pattern from glzr-io/glazewm issue #699: `['move --workspace Gaming', 'set-floating', 'set-fullscreen']`. Before editing, sanity-test that GlazeWM can drive the window's state: focus the window and press `alt+f` (toggle-fullscreen). If it fullscreens, the rule command will too.

## Worked example (2026-08-03)

User: "Playnite opened from Xbox FSE via AnyFSE ends up in half screen mode; want fullscreen." Rules for Playnite.DesktopApp / Playnite.FullscreenApp / AnyFSE were already on disk and live (GlazeWM restarted 11:18, config written 11:05). Window inspection showed the window WAS owned by `Playnite.FullscreenApp` (WPF class `HwndWrapper[Playnite.FullscreenApp.exe;;...]`), rect 2560x1080 on a 2560x1440 primary monitor, showCmd=1 → **floating, not tiled** → the ignore rule worked; Playnite just launched windowed (1080-tall band) via that launch path.

**Outcome:** user decided they want Playnite/AnyFSE *completely unmanaged* (no `set-fullscreen` — that re-engages GlazeWM). Fresh launch of Playnite confirmed the ignore rule works. Lesson: when a rule "doesn't work", first prove tiled-vs-floating via the rect, and test with a fresh app launch before touching the rule.
