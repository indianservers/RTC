# Run explicitly from an elevated PowerShell after configuring runtime.private.json ACLs.
$ErrorActionPreference = 'Stop'
$rtcRoot = Split-Path $PSScriptRoot
$rtcAction = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -File `"$rtcRoot\start-rtc.ps1`" -Production" -WorkingDirectory $rtcRoot
$rtcTrigger = New-ScheduledTaskTrigger -AtStartup
$rtcSettings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName 'RTC Local Enquiry' -Action $rtcAction -Trigger $rtcTrigger -Settings $rtcSettings -User 'SYSTEM' -RunLevel Highest
