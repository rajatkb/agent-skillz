# DLSS scanner — finds nvngx_dlss*.dll in each game root and prints versions.
# Usage:
#   powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\RAJAT\Downloads\dlss-scan.ps1"
# Update $roots to the current drive layout before running (see SKILL.md).
param()

$roots = @(
  "D:\007.First.Light-InsaneRamZes",
  "D:\Black.Myth.Wukong.Digital.Deluxe.Edition-InsaneRamZes",
  "D:\Death.Stranding.2.On.The.Beach.Digital.Deluxe.Edition-InsaneRamZes",
  "D:\Forza.Horizon.6.Premium.Edition-InsaneRamZes",
  "D:\Halo.Campaign.Evolved.Premium.Edition-InsaneRamZes",
  "D:\Kingdom.Come.Deliverance.II.Gold.Edition-InsaneRamZes",
  "D:\PRAGMATA.Deluxe.Edition-InsaneRamZes",
  "D:\The.Last.of.Us.Part.II.Remastered",
  "D:\SteamLibrary\steamapps\common\Dead Space (2023)",
  "D:\SteamLibrary\steamapps\common\AFOP",
  "F:\Cyberpunk.2077.GOG.Rip-InsaneRamZes",
  "F:\Dying.Light.The.Beast.Deluxe.Edition-InsaneRamZes",
  "F:\Ghost of Tsushima (2020-2024)",
  "F:\God of War - Ragnarok",
  "F:\Horizon Forbidden West Complete Edition (2022-2024)",
  "F:\Red Dead Redemption",
  "F:\Resident Evil Requiem",
  "F:\STALKER 2",
  "F:\SteamLibrary\steamapps\common\Dead Cells",
  "F:\SteamLibrary\steamapps\common\Helldivers 2",
  "F:\SteamLibrary\steamapps\common\INSIDE"
)

foreach ($root in $roots) {
  if (-not (Test-Path $root)) { Write-Output "=== MISSING: $root"; continue }
  Write-Output "=== $root"
  $dlls = Get-ChildItem -Path $root -Recurse -Filter "nvngx_dlss*.dll" -File -ErrorAction SilentlyContinue
  if (-not $dlls) { Write-Output "  (no DLSS DLLs found)"; continue }
  foreach ($d in $dlls) {
    try {
      $v = $d.VersionInfo
      $rel = $d.FullName.Substring($root.Length).TrimStart('\')
      Write-Output ("  {0} | FileVer={1} | ProdVer={2}" -f $rel, $v.FileVersion, $v.ProductVersion)
    } catch {
      Write-Output ("  {0} | <unreadable>" -f $d.FullName)
    }
  }
}
