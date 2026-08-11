Write-Output "Focus Assist Status:"
$nfp = Get-ItemProperty 'HKCU:\Control Panel\Notifications' -ErrorAction SilentlyContinue
if ($nfp) {
    $nfp | Format-List
} else {
    Write-Output "No notifications key found"
}
Write-Output "---"
Write-Output "Quiet Hours:"
Get-ItemProperty 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Notifications\QuietHours' -ErrorAction SilentlyContinue | Select-Object QuietHoursServiceState, FullScreenProcess
