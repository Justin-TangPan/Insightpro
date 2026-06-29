<#
.SYNOPSIS
  InsightPro watchdog - monitor ports 3000(frontend) and 8000(backend)
#>

$ProjectRoot  = "C:\Users\Administrator\Desktop\Project\traeproject\insight-web"
$BackendDir   = "$ProjectRoot\backend"
$FrontendDir  = "$ProjectRoot\frontend"
$LogFile      = "$ProjectRoot\scripts\watchdog.log"
$VenvPython   = "$BackendDir\venv\Scripts\python.exe"
$Interval     = 30

function Write-Log {
    param([string]$Msg)
    $Time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$Time | $Msg" | Out-File $LogFile -Encoding utf8 -Append
    Write-Host "$Time | $Msg"
}

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

function Get-PortPID {
    param([int]$Port)
    $lines = netstat -ano 2>$null | Select-String ":$Port\s+.*LISTENING"
    foreach ($line in $lines) {
        $parts = $line.ToString().Trim() -split '\s+'
        if ($parts[-1] -match '^\d+$') { return [int]$parts[-1] }
    }
    return $null
}

function Kill-Port {
    param([int]$Port)
    $pid = Get-PortPID $Port
    if ($pid) {
        Write-Log "  -> stop PID $pid on port $Port"
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
}

function Start-Backend {
    Write-Log "[BE] starting..."
    Kill-Port 8000
    $proc = Start-Process -FilePath $VenvPython -ArgumentList "main.py" 
        -WorkingDirectory $BackendDir -NoNewWindow -PassThru 
        -RedirectStandardOutput "$BackendDir\stdout.log" 
        -RedirectStandardError "$BackendDir\stderr.log"
    Write-Log "  -> PID $($proc.Id)"
    for ($i = 0; $i -lt 120; $i += 5) {
        Start-Sleep -Seconds 5
        if (Test-PortAlive 8000) { Write-Log "  [OK] backend ready (${i}s)"; return $true }
    }
    Write-Log "  [!!] backend not ready after 120s"
    return $false
}

function Start-Frontend {
    Write-Log "[FE] starting..."
    Kill-Port 3000
    if (-not (Test-Path "$FrontendDir\node_modules\next")) {
        Write-Log "  -> npm install..."
        Set-Location $FrontendDir
        npm install 2>&1 | Out-Null
    }
    $proc = Start-Process -FilePath "npx.cmd" -ArgumentList "next start -p 3000" 
        -WorkingDirectory $FrontendDir -NoNewWindow -PassThru 
        -RedirectStandardOutput "$FrontendDir\stdout.log" 
        -RedirectStandardError "$FrontendDir\stderr.log"
    Write-Log "  -> PID $($proc.Id)"
    Start-Sleep -Seconds 10
    if (Test-PortAlive 3000) { Write-Log "  [OK] frontend ready"; return $true }
    Start-Sleep -Seconds 10
    if (Test-PortAlive 3000) { Write-Log "  [OK] frontend ready"; return $true }
    Write-Log "  [!!] frontend not ready after 20s"
    return $false
}

Write-Log "========== watchdog start =========="

if (-not (Test-PortAlive 8000)) { Write-Log "[init] backend down"; Start-Backend }
else { Write-Log "[init] backend running" }

if (-not (Test-PortAlive 3000)) { Write-Log "[init] frontend down"; Start-Frontend }
else { Write-Log "[init] frontend running" }

Write-Log "monitoring every $Interval s..."
Write-Log "=================================="

while ($true) {
    Start-Sleep -Seconds $Interval
    $beOk = Test-PortAlive 8000
    $feOk = Test-PortAlive 3000

    if (-not $beOk -and -not $feOk) {
        Write-Log "[DOWN] both down, restart all"
        Kill-Port 3000; Kill-Port 8000
        Start-Sleep -Seconds 2
        Start-Backend; Start-Frontend
    } elseif (-not $beOk) {
        Write-Log "[DOWN] backend down, restarting..."
        Start-Backend
    } elseif (-not $feOk) {
        Write-Log "[DOWN] frontend down, restarting..."
        Start-Frontend
    }
}
