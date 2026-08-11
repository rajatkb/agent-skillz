# Power Plans & Sleep/Hibernate Timers (powercfg + registry forensics)

Worked on: G14 GA403 (S0ix Modern Standby), Win11 25H2. Covers listing/deleting plans, reading/writing sleep-hibernate timers, and attributing *where* a value came from.

## List / delete plans

```powershell
powercfg /list          # (*) marks the ACTIVE plan
powercfg /delete <GUID> # or by name; safe only if NOT the active plan — check the * first
```

## Read sleep/hibernate timers

```powershell
powercfg /q SCHEME_CURRENT SUB_SLEEP
```

Settings under SUB_SLEEP (238c9fa8-0aad-41ed-83f4-97be242c8f20):

| Setting GUID | Alias | Meaning |
|---|---|---|
| 29f6c1db-86da-48c5-9fdb-f2b67b1f44da | STANDBYIDLE | Sleep after (seconds, 0 = never) |
| 9d7815a6-7ee4-497e-8888-515a05f02364 | HIBERNATEIDLE | Hibernate after (seconds, 0 = never) |
| 94ac6d29-73ce-41a6-809f-6363ba21b47e | HYBRIDSLEEP | Allow hybrid sleep (0/1) |
| bd3b718a-0680-4d9d-8ab2-e1d2b4ac806d | RTCWAKE | Allow wake timers |

**Hex decode (values are seconds):** `0x2a300` = 172800 s = **48 h**; `0x258` = 600 s = **10 min**; `0x0` = never. A "never" value on AC + short timers on DC is the classic OEM/tool-tuned signature.

## Set a timer

```powershell
powercfg /setacvalueindex SCHEME_CURRENT SUB_SLEEP 9d7815a6-7ee4-497e-8888-515a05f02364 0   # hibernate-after AC = never
powercfg /setactive SCHEME_CURRENT
```

(Use `/setdcvalueindex` for the battery side.) Verify with `powercfg /q` — the change takes effect immediately on the active scheme; no reboot needed.

## Modern Standby caveat

On S0ix systems `powercfg /a` reports "Hybrid Sleep not available" (S3 unsupported) — HYBRIDSLEEP=1 is then a **no-op**. But the HIBERNATEIDLE timer still applies during S0ix sleep: a system asleep on AC will transition to hibernate after the AC hibernate-after interval, even with Modern Standby. If the user wants "sleep on AC never hibernates", the AC HIBERNATEIDLE index must be 0.

## Provenance forensics — "how did this value get set?"

Live values live in the per-scheme registry store (readable non-elevated via `reg.exe query`):

```
HKLM\SYSTEM\CurrentControlSet\Control\Power\User\PowerSchemes\<schemeGUID>\<subgroupGUID>\<settingGUID>
    ACSettingIndex   REG_DWORD
    DCSettingIndex   REG_DWORD
```

Attribution rules:

- **Scheme GUID 381b4222-f694-41f0-9685-ff5bb260df2e = stock Microsoft Balanced.** Non-default values under it mean the stock scheme was modified in place (OEM image / tuning tool / manual), NOT that a separate plan is responsible.
- **Imported plans (e.g. Winhanced, ASUS Recommended) have their own GUID** and cannot touch the stock Balanced scheme — check GUIDs before blaming a deleted/other plan. Deleting an imported plan removes only its own values.
- **`HKLM\...\Control\Power\DefaultPowerSchemeValues` (the factory snapshot) is often ABSENT on modern builds** — stock scheme factory defaults are compiled into the power engine, so there is no registry diff to compare against. Don't burn time looking for it.
- Aggressive DC timers (3 min sleep / 10 min hibernate) + 48 h AC hibernate = ASUS/OEM-tuned plan pattern on G14 images.
- Key **timestamps** (when a value was last written) are the only way to pin the exact culprit tool/date. See pitfall below — from WSL you may need regedit.

## Pitfall: WSL interop — PS registry provider can't read key timestamps

From WSL, `Get-Item` / `Get-ChildItem` on these HKLM power keys returns **null `LastWriteTime`** ("You cannot call a method on a null-valued expression") even though `Test-Path` is True and `reg.exe query` returns values fine. `Test-Path` works; timestamps don't. Workarounds:

- Values → `reg.exe query "<key path>"` (reliable).
- Timestamps → regedit (key's "Modified" column in status bar), or an elevated Windows-side PS session. Don't loop over PowerShell provider variants probing for LastWriteTime — it will keep returning null and burn tokens.

## Worked example (this machine)

User wanted: asleep on AC → never hibernate. Actual: HIBERNATEIDLE AC = 0x2a300 (48 h) in stock Balanced → fixed with `/setacvalueindex ... 9d7815a6-... 0` + `/setactive`. DC side left at 3 min sleep / 10 min hibernate.
