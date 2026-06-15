$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$python = (Get-Command python).Source
$taskName = "BailingDailyCollection"
$script = Join-Path $root "backend\pipeline.py"

$action = New-ScheduledTaskAction -Execute $python -Argument "`"$script`"" -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Daily -At 7:00AM
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "百灵每日采集：抓取信源、去重入库、更新静态页面数据。" -Force

Write-Host "Installed task: $taskName"
Write-Host "Runs daily at 07:00. Script: $script"

