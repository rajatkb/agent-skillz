#!/usr/bin/env pwsh
# Hermes Windows Toast Notification Helper
# Used by cron jobs to deliver results as Windows toast notifications
param(
    [string]$Title = "Hermes Agent",
    [string]$Message = "Task completed",
    [int]$Duration = 8
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$iconPath = "$env:USERPROFILE\.hermes\icon.ico"
if (-not (Test-Path $iconPath)) {
    # Use a default system icon
    $iconPath = [System.Drawing.Icon]::ExtractAssociatedIcon((Get-Command powershell.exe).Source)
}

$notify = New-Object System.Windows.Forms.NotifyIcon
$notify.Icon = [System.Drawing.Icon]::ExtractAssociatedIcon((Get-Command pwsh.exe).Source)
$notify.BalloonTipIcon = [System.Windows.Forms.ToolTipIcon]::Info
$notify.BalloonTipTitle = $Title
$notify.BalloonTipText = $Message
$notify.Visible = $true
$notify.ShowBalloonTip($Duration * 1000)

# Clean up after the notification
Start-Sleep -Seconds ($Duration + 2)
$notify.Dispose()
