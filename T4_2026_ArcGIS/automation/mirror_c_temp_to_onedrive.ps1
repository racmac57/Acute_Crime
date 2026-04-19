#Requires -Version 5.1
<#
.SYNOPSIS
  One-way mirror: C:\TEMP -> OneDrive\TEMP (robocopy /MIR).

.DESCRIPTION
  Keeps the OneDrive folder identical to C:\TEMP. Files removed from C:\TEMP are
  removed from the destination on the next run (/MIR).

  WARNING: /MIR deletes files in the destination that no longer exist in the source.
  Large or volatile C:\TEMP contents will sync to OneDrive and count against quota.

.PARAMETER ListOnly
  Dry run (robocopy /L) — lists what would copy without changing anything.

.EXAMPLE
  .\mirror_c_temp_to_onedrive.ps1
.EXAMPLE
  .\mirror_c_temp_to_onedrive.ps1 -ListOnly
#>
[CmdletBinding()]
param(
    [string]$Source = 'C:\TEMP',
    [string]$Dest = $(Join-Path $env:USERPROFILE 'OneDrive - City of Hackensack\TEMP'),
    [switch]$ListOnly
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $Source)) {
    Write-Error "Source does not exist: $Source"
}

if (-not (Test-Path -LiteralPath $Dest)) {
    New-Item -ItemType Directory -Path $Dest -Force | Out-Null
    Write-Host "Created destination: $Dest"
}

$logDir = Join-Path $Dest '.mirror_logs'
if (-not (Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$logFile = Join-Path $logDir "robocopy_$stamp.log"

# /MIR      = mirror (sync + delete extras in dest)
# /Z        = restartable mode
# /FFT      = assume FAT file times (helps across filesystem quirks)
# /R:2 /W:5 = retry open files briefly (OneDrive may lock)
# /MT:8     = multi-thread copy
# /XJ       = exclude junction points (avoid accidental recursion)
# /NP /NDL  = leaner log; /LOG+ appends-style single file per run
$robArgs = @(
    $Source
    $Dest
    '/MIR'
    '/Z'
    '/FFT'
    '/R:2'
    '/W:5'
    '/MT:8'
    '/XJ'
    '/NP'
    '/NDL'
    '/LOG:' + $logFile
)
if ($ListOnly) {
    $robArgs += '/L'
}

Write-Host "Source:  $Source"
Write-Host "Dest:    $Dest"
Write-Host "Log:     $logFile"
if ($ListOnly) { Write-Host 'Mode:    LIST ONLY (no changes)' }

& robocopy.exe @robArgs
$exit = $LASTEXITCODE

# Robocopy: 0-7 = success with different meanings; 8+ = failure
if ($exit -ge 8) {
    Write-Error "Robocopy failed with exit code $exit. See log: $logFile"
}

Write-Host "Robocopy finished (exit $exit). See: $logFile"
