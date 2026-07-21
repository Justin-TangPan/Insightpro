<#
.SYNOPSIS
  InsightPro watchdog - monitor ports 3000(frontend) and 8000(backend)
#>

# --- Auto-detect project root from script location ---
$ScriptDir     = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot   = Split-Path -Parent $ScriptDir
$BackendDir    = Join-Path $ProjectRoot "backend"
$FrontendDir   = Join-Path $ProjectRoot "frontend"
$LogFile       = Join-Path $ScriptDir "watchdog.log"
$LogFileOld    = Join-Path $ScriptDir "watchdog.log.old"
$VenvPython    = Join-Path $BackendDir "venv\Scripts\python.exe"
$Interval      = 30

# --- Restart throttling ---
$MaxConsecutiveRestarts = 5
$BackoffMinutes        = 10
$RestartCountBE        = 0
$RestartCountFE        = 0
$BackoffUntilBE        = $null
$BackoffUntilFE        = $null

# --- Log rotation (5 MB) ---
$LogRotateThreshold = 5 * 1024 * 1024

function Rotate-Log {
    if ((Test-Path $LogFile) -and ((Get-Item $LogFile).Length -gt $LogRotateThreshold)) {
        if (Test-Path $LogFileOld) { Remove-Item $LogFileOld -Force }
        Move-Item $LogFile $LogFileOld -Force
        Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | [log] rotated watchdog.log -> watchdog.log.old"
    }
}

function Write-Log {
    param([string]$Msg)
    Rotate-Log
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
    }
    # wait for port to fully release (avoid TIME_WAIT -> 10048 bind error)
    for ($i = 0; $i -lt 15; $i++) {
        if (-not (Test-PortAlive $Port)) { return }
        Start-Sleep -Seconds 1
    }
    Write-Log "  -> warn: port $Port still in use after 15s"
}

function Start-Backend {
    Write-Log "[BE] starting..."
    for ($attempt = 1; $attempt -le 2; $attempt++) {
        Kill-Port 8000
        $proc = Start-Process -FilePath $VenvPython -ArgumentList "main.py" `
            -WorkingDirectory $BackendDir -NoNewWindow -PassThru `
            -RedirectStandardOutput "$BackendDir\stdout.log" `
            -RedirectStandardError "$BackendDir\stderr.log"
        Write-Log "  -> PID $($proc.Id) (attempt $attempt)"
        for ($i = 0; $i -lt 120; $i += 5) {
            Start-Sleep -Seconds 5
            if (Test-PortAlive 8000) { Write-Log "  [OK] backend ready (${i}s)"; return $true }
            # if process exited early, retry instead of waiting full 120s
            if ($proc.HasExited) { Write-Log "  -> process exited (code $($proc.ExitCode)), will retry"; break }
        }
    }
    Write-Log "  [!!] backend not ready after retries"
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
    $proc = Start-Process -FilePath "npx.cmd" -ArgumentList "next start -p 3000" `
        -WorkingDirectory $FrontendDir -NoNewWindow -PassThru `
        -RedirectStandardOutput "$FrontendDir\stdout.log" `
        -RedirectStandardError "$FrontendDir\stderr.log"
    Write-Log "  -> PID $($proc.Id)"
    # Wait up to 40s for frontend (4 checks at 10s intervals)
    for ($i = 1; $i -le 4; $i++) {
        Start-Sleep -Seconds 10
        if (Test-PortAlive 3000) { Write-Log "  [OK] frontend ready ($($i * 10)s)"; return $true }
    }
    Write-Log "  [!!] frontend not ready after 40s"
    return $false
}

function Test-Backoff {
    param([string]$Service, [ref]$Count, [ref]$BackoffUntil)
    $now = Get-Date
    # If we are in a backoff window, skip restart
    if ($BackoffUntil.Value -and $now -lt $BackoffUntil.Value) {
        $remaining = ($BackoffUntil.Value - $now).ToString("mm\:ss")
        Write-Log "[$Service] backoff active, ${remaining} remaining (restart count $($Count.Value)/$MaxConsecutiveRestarts)"
        return $false
    }
    # If backoff just expired, reset counter
    if ($BackoffUntil.Value -and $now -ge $BackoffUntil.Value) {
        Write-Log "[$Service] backoff expired, resetting restart counter"
        $Count.Value = 0
        $BackoffUntil.Value = $null
    }
    return $true
}

function Register-Restart {
    param([string]$Service, [ref]$Count, [ref]$BackoffUntil)
    $Count.Value++
    Write-Log "[$Service] consecutive restart count: $($Count.Value)/$MaxConsecutiveRestarts"
    if ($Count.Value -ge $MaxConsecutiveRestarts) {
        $BackoffUntil.Value = (Get-Date).AddMinutes($BackoffMinutes)
        Write-Log "[$Service] threshold reached, backing off until $($BackoffUntil.Value.ToString('yyyy-MM-dd HH:mm:ss'))"
    }
}

function Reset-RestartCount {
    param([ref]$Count, [ref]$BackoffUntil)
    if ($Count.Value -gt 0) {
        $Count.Value = 0
        $BackoffUntil.Value = $null
    }
}

Write-Log "========== watchdog start =========="
Write-Log "  project root: $ProjectRoot"
Write-Log "  log file:     $LogFile"
Write-Log "  venv python:  $VenvPython"

if (-not (Test-PortAlive 8000)) { Write-Log "[init] backend down"; Start-Backend }
else { Write-Log "[init] backend running" }

if (-not (Test-PortAlive 3000)) { Write-Log "[init] frontend down"; Start-Frontend }
else { Write-Log "[init] frontend running" }

Write-Log "monitoring every $Interval s..."
Write-Log "  max consecutive restarts: $MaxConsecutiveRestarts"
Write-Log "  backoff duration:         $BackoffMinutes min"
Write-Log "=================================="

while ($true) {
    Start-Sleep -Seconds $Interval
    $beOk = Test-PortAlive 8000
    $feOk = Test-PortAlive 3000

    # Reset counters on successful health
    if ($beOk) { Reset-RestartCount ([ref]$RestartCountBE) ([ref]$BackoffUntilBE) }
    if ($feOk) { Reset-RestartCount ([ref]$RestartCountFE) ([ref]$BackoffUntilFE) }

    if (-not $beOk -and -not $feOk) {
        Write-Log "[DOWN] both down, restart all"
        $canBE = Test-Backoff "BE" ([ref]$RestartCountBE) ([ref]$BackoffUntilBE)
        $canFE = Test-Backoff "FE" ([ref]$RestartCountFE) ([ref]$BackoffUntilFE)
        Kill-Port 3000; Kill-Port 8000
        Start-Sleep -Seconds 2
        if ($canBE) { Start-Backend; Register-Restart "BE" ([ref]$RestartCountBE) ([ref]$BackoffUntilBE) }
        if ($canFE) { Start-Frontend; Register-Restart "FE" ([ref]$RestartCountFE) ([ref]$BackoffUntilFE) }
    } elseif (-not $beOk) {
        Write-Log "[DOWN] backend down, restarting..."
        if (Test-Backoff "BE" ([ref]$RestartCountBE) ([ref]$BackoffUntilBE)) {
            Start-Backend
            Register-Restart "BE" ([ref]$RestartCountBE) ([ref]$BackoffUntilBE)
        }
    } elseif (-not $feOk) {
        Write-Log "[DOWN] frontend down, restarting..."
        if (Test-Backoff "FE" ([ref]$RestartCountFE) ([ref]$BackoffUntilFE)) {
            Start-Frontend
            Register-Restart "FE" ([ref]$RestartCountFE) ([ref]$BackoffUntilFE)
        }
    }
}
