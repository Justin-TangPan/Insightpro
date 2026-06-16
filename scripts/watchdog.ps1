<#
.SYNOPSIS
  InsightPro 服务看门狗 — 监控 3000(前端) 和 8000(后端) 端口
  服务挂掉时自动拉起，日志写入 scripts/watchdog.log
  支持静默后台运行：双击或在 PowerShell 中执行即可
#>

$ProjectRoot  = "C:\Users\Administrator\Desktop\Project\traeproject\insight-web"
$BackendDir   = "$ProjectRoot\backend"
$FrontendDir  = "$ProjectRoot\frontend"
$LogFile      = "$ProjectRoot\scripts\watchdog.log"
$VenvPython   = "$BackendDir\venv\Scripts\python.exe"
$Interval     = 30  # 每 30 秒检测一次

# 日志函数
function Write-Log {
    param([string]$Msg)
    $Time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$Time | $Msg" | Out-File $LogFile -Encoding utf8 -Append
    Write-Host "$Time | $Msg"
}

# 检测端口是否存活
function Test-PortAlive {
    param([int]$Port, [int]$TimeoutMs = 3000)
    try {
        $tcp = [System.Net.Sockets.TcpClient]::new()
        $async = $tcp.BeginConnect("127.0.0.1", $Port, $null, $null)
        $ok = $async.AsyncWaitHandle.WaitOne($TimeoutMs, $false)
        if ($ok -and $tcp.Connected) {
            $tcp.EndConnect($async) | Out-Null
            $tcp.Close()
            return $true
        }
        $tcp.Close()
        return $false
    } catch { return $false }
}

# 查端口对应的 PID
function Get-PortPID {
    param([int]$Port)
    $lines = netstat -ano 2>$null | Select-String ":$Port\s+.*LISTENING"
    foreach ($line in $lines) {
        $parts = $line.ToString().Trim() -split '\s+'
        if ($parts[-1] -match '^\d+$') { return [int]$parts[-1] }
    }
    return $null
}

# 杀进程
function Kill-Port {
    param([int]$Port)
    $pid = Get-PortPID $Port
    if ($pid) {
        Write-Log "  → 停止 PID $pid (端口 $Port)"
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
}

# 启动后端
function Start-Backend {
    Write-Log "[后端] 启动中..."
    Kill-Port 8000
    $proc = Start-Process -FilePath $VenvPython -ArgumentList "main.py" `
        -WorkingDirectory $BackendDir -NoNewWindow -PassThru `
        -RedirectStandardOutput "$BackendDir\stdout.log" `
        -RedirectStandardError "$BackendDir\stderr.log"
    Write-Log "  → PID $($proc.Id)（bge-m3 模型加载需 ~90 秒，请耐心等待）"
    # 等最多 120 秒
    for ($i = 0; $i -lt 120; $i += 5) {
        Start-Sleep -Seconds 5
        if (Test-PortAlive 8000) { Write-Log "  ✅ 后端就绪（耗时 ${i}s）"; return $true }
    }
    Write-Log "  ⚠️ 后端未在 120s 内就绪，请检查 main.py"
    return $false
}

# 启动前端
function Start-Frontend {
    Write-Log "[前端] 启动中..."
    Kill-Port 3000
    # 确保 node_modules
    if (-not (Test-Path "$FrontendDir\node_modules\next")) {
        Write-Log "  → 运行 npm install..."
        Set-Location $FrontendDir
        npm install 2>&1 | Out-Null
    }
    $proc = Start-Process -FilePath "npx.cmd" -ArgumentList "next start -p 3000" `
        -WorkingDirectory $FrontendDir -NoNewWindow -PassThru `
        -RedirectStandardOutput "$FrontendDir\stdout.log" `
        -RedirectStandardError "$FrontendDir\stderr.log"
    Write-Log "  → PID $($proc.Id)"
    Start-Sleep -Seconds 10
    if (Test-PortAlive 3000) { Write-Log "  ✅ 前端就绪"; return $true }
    Start-Sleep -Seconds 10
    if (Test-PortAlive 3000) { Write-Log "  ✅ 前端就绪"; return $true }
    Write-Log "  ⚠️ 前端未能在 20s 内就绪"
    return $false
}

# ====== 启动 ======
Clear-Host
Write-Host ""
Write-Host "  ╔═══════════════════════════════════════════════╗"
Write-Host "  ║       InsightPro 服务看门狗 v1.0              ║"
Write-Host "  ║       监控 3000 (前端) + 8000 (后端)          ║"
Write-Host "  ║       每 $Interval 秒检测一次                   ║"
Write-Host "  ╚═══════════════════════════════════════════════╝"
Write-Host ""
Write-Log "========== 看门狗启动 =========="

# 初始检查与启动
if (-not (Test-PortAlive 8000)) { Write-Log "[首次] 后端未运行"; Start-Backend }
else { Write-Log "[首次] 后端已在运行 ✅" }

if (-not (Test-PortAlive 3000)) { Write-Log "[首次] 前端未运行"; Start-Frontend }
else { Write-Log "[首次] 前端已在运行 ✅" }

Write-Log "进入监控循环..."
Write-Log "=================================="

# ====== 监控循环 ======
while ($true) {
    Start-Sleep -Seconds $Interval
    $beOk = Test-PortAlive 8000
    $feOk = Test-PortAlive 3000

    if (-not $beOk -and -not $feOk) {
        Write-Log "[故障] 前后端全部挂掉，全部重启"
        Kill-Port 3000; Kill-Port 8000
        Start-Sleep -Seconds 2
        Start-Backend; Start-Frontend
    } elseif (-not $beOk) {
        Write-Log "[故障] 后端挂掉，重启..."
        Start-Backend
    } elseif (-not $feOk) {
        Write-Log "[故障] 前端挂掉，重启..."
        Start-Frontend
    }
    # 都健康时不输出日志（安静模式）
}
