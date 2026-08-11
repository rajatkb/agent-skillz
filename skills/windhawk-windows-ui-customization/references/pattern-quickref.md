# Windhawk Taskbar Clock Customization — Pattern Quick Reference

Full pattern table extracted from v1.8 mod source (`ramensoftware/windhawk-mods`).

## Time/Date/Calendar

| Pattern | Description |
|---|---|
| `%time%` | Time per TimeFormat setting |
| `%time2%`, `%time3%` etc. | Additional time formats (separated by `;` in TimeFormat) |
| `%time_tz1%`, `%time_tz2%` | Time in custom time zones |
| `%date%` | Date per DateFormat setting |
| `%date2%`, `%date3%` | Additional date formats |
| `%date_tz1%`, `%date_tz2%` | Date in custom time zones |
| `%weekday%` | Weekday per WeekdayFormat setting |
| `%weekday_tz1%` | Weekday in custom time zone |
| `%weekday_num%` | Weekday number (1-7, per system first-day-of-week setting) |
| `%weeknum%` | Week number (week containing Jan 1 = week 1) |
| `%weeknum_iso%` | ISO week number |
| `%dayofyear%` | Day of year |
| `%timezone%` | Timezone in ISO 8601 format |

## System Performance

| Pattern | Description |
|---|---|
| `%cpu%` | CPU usage % |
| `%cpu_temp%` | CPU temperature in °C (avg of ACPI thermal zones) |
| `%cpu_temp_f%` | CPU temperature in °F |
| `%ram%` | RAM usage % |
| `%ram_used%` | Used RAM in GB |
| `%ram_total%` | Total RAM in GB |
| `%ram_committed%` | Committed RAM usage % |
| `%ram_committed_used%` | Used committed RAM in GB |
| `%ram_committed_total%` | Total committed RAM in GB |
| `%gpu%` | GPU usage % |
| `%vram%` | VRAM usage % of total dedicated |
| `%vram_used%` | Used dedicated VRAM in GB |
| `%vram_total%` | Total dedicated VRAM in GB |
| `%vram_shared%` | Shared VRAM usage % |
| `%vram_shared_used%` | Used shared VRAM in GB |
| `%vram_shared_total%` | Total shared VRAM pool in GB |
| `%upload_speed%` | System-wide upload transfer rate |
| `%download_speed%` | System-wide download transfer rate |
| `%total_speed%` | Combined upload + download |
| `%disk_read%` | Disk read speed |
| `%disk_write%` | Disk write speed |
| `%disk_total%` | Combined disk read + write |
| `%battery%` | Battery level % |
| `%battery_time%` | Battery time remaining (h:mm format) |
| `%power%` | Battery power in watts (negative = discharging) |

## Media Player (GSMTC-compatible)

| Pattern | Description |
|---|---|
| `%media_title%` | Currently playing media title |
| `%media_artist%` | Currently playing media artist |
| `%media_album%` | Currently playing media album |
| `%media_status%` | Playback status icon (⏯ ⏸ ⏹) |
| `%media_info%` | Combined "Artist — Title", truncated with ellipsis |

## Web & Weather

| Pattern | Description |
|---|---|
| `%weather%` | Weather from wttr.in |
| `%web1%` to `%web9%` | Web content item, truncated |
| `%web1_full%` to `%web9_full%` | Full web content item |

## Formatting

| Pattern | Description |
|---|---|
| `%n%` or `%newline%` | Newline character |

## Config Settings (selected)

| Setting | Description |
|---|---|
| `ShowSeconds` | 0 or 1 |
| `TimeFormat` | Win32 time format string |
| `DateFormat` | Win32 date format string |
| `WeekdayFormat` | `dddd`, `ddd`, or `custom` |
| `TopLine` | Upper tile text |
| `BottomLine` | Lower tile text |
| `MiddleLine` | Middle tile (Win10 only) |
| `TooltipLine` | Tooltip text |
| `TooltipLineMode` | `append` or `replace` |
| `Width` | Clock width (Win10) |
| `Height` | Clock height (Win10) |
| `MaxWidth` | Max width (Win11) |
| `TextSpacing` | Line spacing |
| `TimeStyle` | Block: TextColor, TextAlignment, FontSize, FontFamily, FontWeight, FontStyle, FontStretch, CharacterSpacing, LineHeight |
| `DateStyle` | Same sub-fields as TimeStyle |
| `WebContentsItems` | Array of URL/BlockStart/Start/End/ContentMode/SearchReplace/MaxLength |
| `WebContentsUpdateInterval` | Minutes between web updates |
| `DataCollection.UpdateInterval` | Seconds between performance metric updates |
| `DataCollection.NetworkMetricsFormat` | `mbs`, `mbsNumberOnly`, `mbsDynamic`, `mbits`, etc. |
| `DataCollection.PercentageFormat` | `spacePaddingAndSymbol`, `spacePadding`, `singleSpacePadding`, `zeroPadding`, `noPadding` |

## TimeStyle / DateStyle fields

| Field | Values |
|---|---|
| `TextColor` | Color name, `#RGB`, `#ARGB` |
| `TextAlignment` | Default, Right, Center, Left, Justify |
| `FontSize` | 0 = default |
| `FontFamily` | Any installed font |
| `FontWeight` | Thin, ExtraLight, Light, SemiLight, Normal, Medium, SemiBold, Bold, ExtraBold, Black, ExtraBlack |
| `FontStyle` | Normal, Oblique, Italic |
| `FontStretch` | Undefined, UltraCondensed, ExtraCondensed, Condensed, SemiCondensed, Normal, SemiExpanded, Expanded, ExtraExpanded, UltraExpanded |
| `CharacterSpacing` | Positive or negative |
| `LineHeight` | Pixels, 0 = default |
