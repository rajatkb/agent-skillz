<#
.SYNOPSIS
  Click at screen coordinates, optionally type text, then restore focus.
  Fallback when UIA can't find the target element in the accessibility tree.

.PARAMETER X
  Screen X coordinate (absolute pixels)
.PARAMETER Y
  Screen Y coordinate (absolute pixels)
.PARAMETER Type
  Text to type via SendKeys after clicking (optional)
.PARAMETER NoRestore
  Skip restoring focus to the previous window

.EXAMPLE
  # Click at position and type into the focused field
  powershell.exe -ExecutionPolicy Bypass -File click-at.ps1 -X 390 -Y 476 -Type "Guwahati"

.EXAMPLE
  # Just click, no typing
  powershell.exe -ExecutionPolicy Bypass -File click-at.ps1 -X 170 -Y 370
#>
param(
  [int]$X,
  [int]$Y,
  [string]$Type = "",
  [switch]$NoRestore
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, UIntPtr dwExtraInfo);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  public const uint LEFTDOWN = 0x0002;
  public const uint LEFTUP = 0x0004;
}
"@

$prevHwnd = [Win32]::GetForegroundWindow()

[Win32]::SetCursorPos($X, $Y)
Start-Sleep -Milliseconds 100
[Win32]::mouse_event([Win32]::LEFTDOWN, 0, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 50
[Win32]::mouse_event([Win32]::LEFTUP, 0, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 200

if ($Type) {
  $wshell = New-Object -ComObject WScript.Shell
  Start-Sleep -Milliseconds 100
  $wshell.SendKeys($Type)
  Start-Sleep -Milliseconds 200
}

if (-not $NoRestore -and $prevHwnd -ne [IntPtr]::Zero) {
  Start-Sleep -Milliseconds 100
  [Win32]::SetForegroundWindow($prevHwnd)
  Write-Output "Focus restored to HWND $prevHwnd"
}

Write-Output "Clicked at ($X, $Y)" + $(if ($Type) { ", typed '$Type'" } else { "" })
