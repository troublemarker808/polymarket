param(
    [string]$ConfigDir = "configs",
    [string]$StatePath = "data/runtime/runtime_state.paper-supervisor.current.json",
    [string]$LogPath = "data/runtime/paper-supervisor.current.log",
    [string]$PidPath = "data/runtime/paper-supervisor.current.pid",
    [string]$EventPath = "data/runtime/paper-events.current.jsonl",
    [string]$MetricsPath = "data/runtime/paper-metrics.latest.json",
    [string]$SnapshotCapturePath = "",
    [string]$HealthCheckScriptPath = "scripts/check-paper-health.ps1",
    [string]$HealthReportPath = "data/runtime/paper-health.latest.md",
    [int]$MaxPages = 1,
    [int]$IntervalSeconds = 30,
    [int]$SummaryEverySnapshots = 50,
    [int]$MaxCycles = 0,
    [int]$MaxMarketSnapshots = 0,
    [switch]$ExcludeBootstrapFromLimit
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

function Resolve-ManagedPath {
    param([string]$PathValue)
    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        return $PathValue
    }
    return Join-Path $repoRoot $PathValue
}

function Write-RunLog {
    param(
        [string]$ResolvedLogPath,
        [string]$Message
    )
    Add-Content -Path $ResolvedLogPath -Value $Message -Encoding UTF8
}

$resolvedStatePath = Resolve-ManagedPath $StatePath
$resolvedLogPath = Resolve-ManagedPath $LogPath
$resolvedPidPath = Resolve-ManagedPath $PidPath
$resolvedEventPath = Resolve-ManagedPath $EventPath
$resolvedMetricsPath = Resolve-ManagedPath $MetricsPath
$resolvedSnapshotCapturePath = if ([string]::IsNullOrWhiteSpace($SnapshotCapturePath)) { "" } else { Resolve-ManagedPath $SnapshotCapturePath }
$resolvedHealthCheckScriptPath = Resolve-ManagedPath $HealthCheckScriptPath
$resolvedHealthReportPath = Resolve-ManagedPath $HealthReportPath

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $resolvedStatePath) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $resolvedLogPath) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $resolvedPidPath) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $resolvedEventPath) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $resolvedMetricsPath) | Out-Null
if (-not [string]::IsNullOrWhiteSpace($resolvedSnapshotCapturePath)) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $resolvedSnapshotCapturePath) | Out-Null
}
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $resolvedHealthReportPath) | Out-Null

Set-Content -Path $resolvedPidPath -Value "$PID" -Encoding ASCII
Write-RunLog -ResolvedLogPath $resolvedLogPath -Message "=== supervisor_start $(Get-Date -Format o)"

$cycle = 0
while ($true) {
    if ($MaxCycles -gt 0 -and $cycle -ge $MaxCycles) {
        break
    }

    $cycle += 1
    Write-RunLog -ResolvedLogPath $resolvedLogPath -Message "=== run_start $(Get-Date -Format o)"

    $pythonArgs = @(
        "-m",
        "pm_bot",
        "run-paper-crypto-session",
        "--config-dir",
        $ConfigDir,
        "--max-pages",
        "$MaxPages",
        "--state-path",
        $resolvedStatePath,
        "--event-path",
        $resolvedEventPath,
        "--metrics-path",
        $resolvedMetricsPath,
        "--summary-every-snapshots",
        "$SummaryEverySnapshots"
    )
    if ($MaxMarketSnapshots -gt 0) {
        $pythonArgs += @("--max-market-snapshots", "$MaxMarketSnapshots")
    }
    if ($ExcludeBootstrapFromLimit.IsPresent) {
        $pythonArgs += @("--exclude-bootstrap-from-limit")
    }
    if (-not [string]::IsNullOrWhiteSpace($resolvedSnapshotCapturePath)) {
        $pythonArgs += @("--snapshot-path", $resolvedSnapshotCapturePath)
    }

    & python @pythonArgs 2>&1 | ForEach-Object {
        Write-RunLog -ResolvedLogPath $resolvedLogPath -Message ([string]$_)
    }
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        Write-RunLog -ResolvedLogPath $resolvedLogPath -Message "exit_code=$exitCode"
        Write-RunLog -ResolvedLogPath $resolvedLogPath -Message "issue=paper_command_failed"
    }

    Write-RunLog -ResolvedLogPath $resolvedLogPath -Message "=== run_end $(Get-Date -Format o)"
    if (Test-Path $resolvedHealthCheckScriptPath) {
        try {
            & $resolvedHealthCheckScriptPath -StatePath $resolvedStatePath -LogPath $resolvedLogPath -MetricsPath $resolvedMetricsPath -ReportPath $resolvedHealthReportPath | Out-Null
        } catch {
            Write-RunLog -ResolvedLogPath $resolvedLogPath -Message "health_check_error=$($_.Exception.Message)"
            Write-RunLog -ResolvedLogPath $resolvedLogPath -Message "issue=health_check_failed"
        }
    }

    if ($MaxCycles -gt 0 -and $cycle -ge $MaxCycles) {
        break
    }

    Start-Sleep -Seconds $IntervalSeconds
}

Write-RunLog -ResolvedLogPath $resolvedLogPath -Message "=== supervisor_exit $(Get-Date -Format o)"
