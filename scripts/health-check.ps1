<#
.SYNOPSIS
  InsightPro watchdog - auto restart backend/frontend when down
.DESCRIPTION
  Checks port 3000 (Next.js) and 8000 (FastAPI) every 60s.
  Logs to scripts\health.log
#>

$ProjectRoot   = "C:\Users\Administrator\Desktop\Project\traeproject\insight-web"
$BackendDir    = "$ProjectRoot\backend"
$FrontendDir   = "$ProjectRoot\frontend"
$LogFile       = "$ProjectRoot\scripts\health.log"
$VenvPython    = "$BackendDir\venv\Scripts\python.exe"
$IntervalSec   = 60

function Write-Log {
    param([string]$Message)
    $Time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$Time | $Message" | Out-File -FilePath $LogFile -Encoding utf8 -Append
    Write-Host "$Time | $Message"
}

function Test-Port {
    param([int]$Port, [int]$TimeoutMs = 3000)
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
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

function Get-PidByPort {
    param([int]$Port)
    try {
        $lines = netstat -ano | Select-String (":$Port\s+.*LISTENING")
        foreach ($line in $lines) {
            $parts = $line.ToString().Trim() -split '\s+'
            $pid = $parts[-1]
            if ($pid -match '^\d+$') { return [int]$pid }
        }
    } catch {}
    return $null
}

function Kill-ByPort {
    param([int]$Port)
    $pid = Get-PidByPort -Port $Port
    if ($pid) {
        Write-Log "Stopping PID $pid on port $Port"
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 3
        if (Get-PidByPort -Port $Port) {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2
        }
    }
}

function Start-Backend {
    Write-Log "[BE] Starting backend (port 8000)..."
    $null = New-Item -Path "$BackendDir\stdout.log" -ItemType File -Force
    $null = New-Item -Path "$BackendDir\stderr.log" -ItemType File -Force
    $proc = Start-Process -FilePath $VenvPython -ArgumentList "main.py" `
        -WorkingDirectory $BackendDir -NoNewWindow -PassThru `
        -RedirectStandardOutput "$BackendDir\stdout.log" `
        -RedirectStandardError "$BackendDir\stderr.log"
    Write-Log "[BE] PID=$($proc.Id) (waiting ~90s for bge-m3)"
    $maxWait = 120
    for ($i = 0; $i -lt $maxWait; $i += 5) {
        Start-Sleep -Seconds 5
        if (Test-Port -Port 8000) {
            Write-Log "[BE] Backend ready after ${i}s"
            return $true
        }
    }
    Write-Log "[BE] Backend NOT ready after ${maxWait}s"
    return $false
}

function Start-Frontend {
    Write-Log "[FE] Starting frontend (port 3000)..."
    $null = New-Item -Path "$FrontendDir\stdout.log" -ItemType File -Force
    $null = New-Item -Path "$FrontendDir\stderr.log" -ItemType File -Force
    if (-not (Test-Path "$FrontendDir\node_modules\next")) {
        Write-Log "[FE] Running npm install..."
        Set-Location $FrontendDir
        npm install 2>&1 | Out-Null
    }
    $proc = Start-Process -FilePath "npx.cmd" -ArgumentList "next start -p 3000" `
        -WorkingDirectory $FrontendDir -NoNewWindow -PassThru `
        -RedirectStandardOutput "$FrontendDir\stdout.log" `
        -RedirectStandardError "$FrontendDir\stderr.log"
    Write-Log "[FE] PID=$($proc.Id)"
    Start-Sleep -Seconds 12
    if (Test-Port -Port 3000) {
        Write-Log "[FE] Frontend ready"
        return $true
    }
    Start-Sleep -Seconds 10
    if (Test-Port -Port 3000) {
        Write-Log "[FE] Frontend ready"
        return $true
    }
    Write-Log "[FE] Frontend NOT ready"
    return $false
}

# ==== MAIN ====
Write-Log "=== InsightPro watchdog started ==="

if (-not (Test-Port -Port 8000)) {
    Write-Log "[INIT] Backend not running, starting..."
    Start-Backend
} else {
    Write-Log "[INIT] Backend running"
}

if (-not (Test-Port -Port 3000)) {
    Write-Log "[INIT] Frontend not running, starting..."
    Start-Frontend
} else {
    Write-Log "[INIT] Frontend running"
}

Write-Log "=== Monitoring every ${IntervalSec}s ==="

while ($true) {
    Start-Sleep -Seconds $IntervalSec
    $beOk = Test-Port -Port 8000
    $feOk = Test-Port -Port 3000

    if (-not $beOk -and -not $feOk) {
        Write-Log "[DOWN] Both services down - restarting all"
        Kill-ByPort -Port 8000
        Kill-ByPort -Port 3000
        Start-Sleep -Seconds 2
        Start-Backend
        Start-Frontend
    } elseif (-not $beOk) {
        Write-Log "[DOWN] Backend down - restarting"
        Kill-ByPort -Port 8000
        Start-Sleep -Seconds 2
        Start-Backend
    } elseif (-not $feOk) {
        Write-Log "[DOWN] Frontend down - restarting"
        Kill-ByPort -Port 3000
        Start-Sleep -Seconds 2
        Start-Frontend
    }
}
