<#
.SYNOPSIS
    Disable or restore non-essential Windows services on a dev/gaming machine.
.DESCRIPTION
    Default mode: Sets Tier 1 services -> Disabled, Tier 2 services -> Manual.
    -Undo: Restores every service to its original startup type from a backup JSON.
    -Status: Shows current vs intended state without making changes.
    -WhatIf: Preview changes without applying them.
.PARAMETER Undo
    Restore services to original startup types from the backup file.
.PARAMETER Status
    Show current vs intended state for all targeted services. No changes made.
.PARAMETER WhatIf
    Show what would change without actually applying anything.
.PARAMETER LogPath
    Path to the change log. Default: script-dir/debloat-log-<date>.txt
.PARAMETER BackupPath
    Path to the backup JSON. Default: script-dir/service-backup.json
.EXAMPLE
    .\disable-bloat.ps1
    Apply all service changes.
.EXAMPLE
    .\disable-bloat.ps1 -Undo
    Restore all services to original states.
.EXAMPLE
    .\disable-bloat.ps1 -Status
    Preview what would change.
.NOTES
    Run as Administrator. Adjust _XXXX suffix to match your machine.
#>

[CmdletBinding(DefaultParameterSetName = 'Apply')]
param(
    [Parameter(ParameterSetName = 'Undo')]
    [switch]$Undo,

    [Parameter(ParameterSetName = 'Status')]
    [switch]$Status,

    [switch]$WhatIf,

    [string]$LogPath,
    [string]$BackupPath
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $LogPath)  { $LogPath  = Join-Path $ScriptDir "debloat-log-$(Get-Date -Format 'yyyyMMdd-HHmmss').txt" }
if (-not $BackupPath) { $BackupPath = Join-Path $ScriptDir "service-backup.json" }

# --- EDIT THESE ARRAYS for your target machine ---
# Discover your suffix: Get-Service | Where-Object { $_.Name -match '_' }
$Tier1 = @(
    # AMD/ASUS bloat
    'AMD Crash Defender Service'
    'AMD External Events Utility'
    'AmdPpkgSvc'
    'AsusPTPService'
    # Telemetry / data collection
    'DPS'
    'InventorySvc'
    'whesvc'
    'DusmSvc'
    'webthreatdefusersvc_b52fb'  # <-- CHANGE SUFFIX
    # Push notifications
    'WpnService'
    'WpnUserService_b52fb'       # <-- CHANGE SUFFIX
    # Xbox / Store licensing
    'XblAuthManager'
    'ClipSVC'
    'LicenseManager'
    'InstallService'
    # Search / indexing
    'WSearch'
    'SysMain'
    # Background junk
    'DoSvc'
    'Spooler'
    'PhoneSvc'
    'SSDPSRV'
    'SstpSvc'
    'lmhosts'
    'StiSvc'
    'WinHttpAutoProxySvc'
    'DevQueryBroker'
    'DevicesFlowUserSvc_b52fb'   # <-- CHANGE SUFFIX
    'TrkWks'
    'nvagent'
    'AppIDSvc'
    'SharedAccess'
    # Other
    'BcastDVRUserService_b52fb'  # <-- CHANGE SUFFIX
    'CloudflareWARPUpdater'
    'DisplayEnhancementService'
    'DolbyDAXAPI'
    'HvHost'
    'MTKBTSVC'
    'NPSMSvc_b52fb'              # <-- CHANGE SUFFIX
)

$Tier2 = @(
    'GameInputRedistService'
    'GameInputSvc'
    'GamingServices'
    'GamingServicesNet'
    'UsoSvc'
    'BrokerInfrastructure'
    'FontCache'
    'DeviceAssociationService'
    'cbdhsvc_b52fb'              # <-- CHANGE SUFFIX
    'StateRepository'
)

$AllServices = $Tier1 + $Tier2

# --- Helpers ---
function Write-Log {
    param([string]$Message)
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Add-Content -Path $LogPath -Value $line
    Write-Host $line
}

function Get-OriginalStartType {
    param([string]$ServiceName)
    $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if (-not $svc) { return $null }
    try {
        return (Get-CimInstance -ClassName Win32_Service -Filter "Name='$ServiceName'").StartMode
    } catch {
        return $null
    }
}

function Get-IntendedStartType {
    param([string]$ServiceName)
    if ($Tier1 -contains $ServiceName) { return 'Disabled' }
    if ($Tier2 -contains $ServiceName) { return 'Manual' }
    return $null
}

function Set-ServiceStartType {
    param([string]$Name, [string]$StartType)
    try {
        Set-Service -Name $Name -StartupType $StartType -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

# --- Status mode ---
if ($Status) {
    Write-Host "`n=== Service Debloat Status ===`n" -ForegroundColor Cyan
    $anyMissing = $false
    foreach ($name in $AllServices) {
        $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
        if (-not $svc) {
            Write-Host "  [?] $name -- NOT FOUND" -ForegroundColor DarkYellow
            $anyMissing = $true
            continue
        }
        $current = Get-OriginalStartType $name
        $intended = Get-IntendedStartType $name
        $icon = if ($current -eq $intended) { '[OK]' } else { '[CH]' }
        $color = if ($current -eq $intended) { 'Green' } else { 'Red' }
        Write-Host "  $icon [$current -> $intended] $name" -ForegroundColor $color
    }
    if ($anyMissing) {
        Write-Host "`nSome services not found -- update the _XXXX suffix." -ForegroundColor Yellow
    }
    exit 0
}

# --- Undo mode ---
if ($Undo) {
    if (-not (Test-Path $BackupPath)) {
        Write-Host "ERROR: Backup not found at $BackupPath" -ForegroundColor Red
        exit 1
    }
    Write-Host "`n=== Undo Mode ===`n" -ForegroundColor Cyan
    $backup = Get-Content $BackupPath | ConvertFrom-Json
    $restored = 0; $failed = 0
    foreach ($entry in $backup) {
        $svc = Get-Service -Name $entry.Name -ErrorAction SilentlyContinue
        if (-not $svc) { Write-Host "  [?] $($entry.Name) -- not found"; continue }
        if ($WhatIf) { Write-Host "  [?] Would restore $($entry.Name) -> $($entry.OriginalStartType)"; continue }
        if (Set-ServiceStartType $entry.Name $entry.OriginalStartType) {
            Write-Log "UNDO: $($entry.Name) -> $($entry.OriginalStartType)"
            $restored++
        } else { $failed++ }
    }
    Write-Host "`nRestored: $restored  Failed: $failed" -ForegroundColor Cyan
    if ($restored -gt 0 -and -not $WhatIf) { Remove-Item $BackupPath -Force }
    exit 0
}

# --- Apply mode ---
Write-Host "`n=== Windows Service Debloat -- Apply ===`n" -ForegroundColor Cyan
Write-Host "Tier 1 (-> Disabled): $($Tier1.Count)"
Write-Host "Tier 2 (-> Manual):   $($Tier2.Count)"
Write-Host ""

if (-not $WhatIf) {
    $confirm = Read-Host "Continue? (y/N)"
    if ($confirm -ne 'y' -and $confirm -ne 'Y') { Write-Host "Aborted."; exit 0 }
}

Write-Host "`nBacking up current states..." -ForegroundColor Gray
$backupData = @()
foreach ($name in $AllServices) {
    $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
    if (-not $svc) { continue }
    $original = Get-OriginalStartType $name
    if ($original) { $backupData += [PSCustomObject]@{ Name = $name; OriginalStartType = $original } }
}
if (-not $WhatIf) {
    $backupData | ConvertTo-Json | Set-Content $BackupPath -Force
    Write-Host "  Saved -> $BackupPath" -ForegroundColor Gray
}

$changed = 0; $skipped = 0; $errors = 0

Write-Host "`nTier 1 -> Disabled..." -ForegroundColor Yellow
foreach ($name in $Tier1) {
    $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
    if (-not $svc) { Write-Host "  [?] $name -- not found"; $skipped++; continue }
    $current = Get-OriginalStartType $name
    if ($current -eq 'Disabled') { Write-Host "  [=] $name -- already Disabled" -ForegroundColor DarkGray; $skipped++; continue }
    if ($WhatIf) { Write-Host "  [->] $name ($current -> Disabled)" -ForegroundColor Yellow; $changed++; continue }
    if (Set-ServiceStartType $name 'Disabled') {
        Write-Log "CHANGE: $name -> Disabled (was $current)"
        Write-Host "  [OK] $name ($current -> Disabled)" -ForegroundColor Green; $changed++
    } else { Write-Host "  [FAIL] $name ($current -> Disabled)" -ForegroundColor Red; $errors++ }
}

Write-Host "`nTier 2 -> Manual..." -ForegroundColor Yellow
foreach ($name in $Tier2) {
    $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
    if (-not $svc) { Write-Host "  [?] $name -- not found"; $skipped++; continue }
    $current = Get-OriginalStartType $name
    if ($current -eq 'Manual') { Write-Host "  [=] $name -- already Manual" -ForegroundColor DarkGray; $skipped++; continue }
    if ($WhatIf) { Write-Host "  [->] $name ($current -> Manual)" -ForegroundColor Yellow; $changed++; continue }
    if (Set-ServiceStartType $name 'Manual') {
        Write-Log "CHANGE: $name -> Manual (was $current)"
        Write-Host "  [OK] $name ($current -> Manual)" -ForegroundColor Green; $changed++
    } else { Write-Host "  [FAIL] $name ($current -> Manual)" -ForegroundColor Red; $errors++ }
}

Write-Host "`nApplied: $changed  Skipped: $skipped  Errors: $errors" -ForegroundColor Cyan
Write-Host "Undo: .\disable-bloat.ps1 -Undo`n" -ForegroundColor Cyan
