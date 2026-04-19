#Requires -Version 5.1
<#
.SYNOPSIS
  Creates a Scheduled Task to run mirror_c_temp_to_onedrive.ps1 on an interval.

.NOTES
  Run PowerShell elevated only if your execution policy blocks scripts for SYSTEM;
  this registers the task as the current user so OneDrive paths resolve.

  Adjust -IntervalMinutes as needed (default 60).
#>
[CmdletBinding()]
param(
    [string]$TaskName = 'Mirror_C_TEMP_to_OneDrive_TEMP',
    [int]$IntervalMinutes = 60
)

$ErrorActionPreference = 'Stop'

$scriptPath = Join-Path $PSScriptRoot 'mirror_c_temp_to_onedrive.ps1'
if (-not (Test-Path -LiteralPath $scriptPath)) {
    Write-Error "Missing script: $scriptPath"
}

$ps = (Get-Command powershell.exe).Source
$arg = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""

$action = New-ScheduledTaskAction -Execute $ps -Argument $arg
# Repeat every N minutes for a long horizon (avoid [TimeSpan]::MaxValue quirks on some builds)
$start = (Get-Date).AddMinutes(1)
$trigger = New-ScheduledTaskTrigger -Once -At $start -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) -RepetitionDuration (New-TimeSpan -Days 9999)

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null

Write-Host "Registered task '$TaskName' (every $IntervalMinutes min)."
Write-Host "View: Task Scheduler -> Task Scheduler Library -> $TaskName"
