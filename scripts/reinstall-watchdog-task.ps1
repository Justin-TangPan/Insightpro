<#
.SYNOPSIS
  一次性把 InsightProWatchdog 升级为「无论用户是否登录都运行」，
  使开机触发器在 RDP 登录前就能拉起看门狗。需要 Administrator 密码。

  用法: powershell -File scripts\reinstall-watchdog-task.ps1
  会弹窗要求输入 Administrator 密码。
#>
$ErrorActionPreference = "Stop"
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Split-Path -Parent $ScriptDir
$Watchdog    = Join-Path $ScriptDir "watchdog.ps1"

$cred = Get-Credential -UserName "Administrator" -Message "请输入 Administrator 密码（用于计划任务开机自启）"
if (-not $cred) { Write-Host "已取消"; exit 1 }

$action   = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Watchdog`""
$boot     = New-ScheduledTaskTrigger -AtStartup
$logon    = New-ScheduledTaskTrigger -AtLogon
$principal = New-ScheduledTaskPrincipal -UserId $cred.UserName `
    -LogonType Password -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -StartWhenAvailable `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0)

Register-ScheduledTask -TaskName "InsightProWatchdog" `
    -Action $action -Trigger @($boot,$logon) `
    -Principal $principal -Settings $settings -Force -User $cred.UserName -Password $cred.GetNetworkCredential().Password | Out-Null

Write-Host "已重装任务 InsightProWatchdog（开机+登录双触发，登录前可运行）。"
schtasks /Query /TN InsightProWatchdog /V /FO LIST 2>&1 | Select-String "Logon Mode|Schedule Type"
