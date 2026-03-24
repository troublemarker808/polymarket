param(
    [string]$StatePath = "data/runtime/runtime_state.paper-supervisor.current.json",
    [string]$LogPath = "data/runtime/paper-supervisor.current.log",
    [string]$ReportPath = "data/runtime/paper-health.latest.md",
    [int]$StalePendingHours = 4
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

function To-DateTimeOrNull {
    param($Value)
    if ($null -eq $Value -or [string]::IsNullOrWhiteSpace([string]$Value)) {
        return $null
    }
    return [datetimeoffset]::Parse([string]$Value)
}

$resolvedStatePath = Resolve-ManagedPath $StatePath
$resolvedLogPath = Resolve-ManagedPath $LogPath
$resolvedReportPath = Resolve-ManagedPath $ReportPath
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $resolvedReportPath) | Out-Null

$issues = New-Object System.Collections.Generic.List[string]
$paperDays = 0
$completeSamples = 0
$tracebacks = 0
$exitCodes = 0
$lastRunStart = $null
$lastRunEnd = $null

if (Test-Path $resolvedLogPath) {
    $logLines = Get-Content $resolvedLogPath
    $runStartMatches = @($logLines | Where-Object { $_ -match '^=== run_start ' })
    $paperDays = @($runStartMatches | ForEach-Object {
        $raw = ($_ -replace '^=== run_start ', '').Trim()
        ([datetimeoffset]::Parse($raw)).ToString('yyyy-MM-dd')
    } | Sort-Object -Unique).Count
    $completeSamples = @($logLines | Where-Object { $_ -match '^processed_snapshots=' }).Count
    $tracebacks = @($logLines | Where-Object { $_ -match '^Traceback' }).Count
    $exitCodes = @($logLines | Where-Object { $_ -match '^exit_code=' }).Count
    if ($runStartMatches.Count -gt 0) {
        $lastRunStart = [datetimeoffset]::Parse(($runStartMatches[-1] -replace '^=== run_start ', '').Trim())
    }
    $runEndMatches = @($logLines | Where-Object { $_ -match '^=== run_end ' })
    if ($runEndMatches.Count -gt 0) {
        $lastRunEnd = [datetimeoffset]::Parse(($runEndMatches[-1] -replace '^=== run_end ', '').Trim())
    }
} else {
    $issues.Add("log_missing")
}

$state = $null
$openPositions = 0
$pendingOrders = 0
$stalePending = 0

if (Test-Path $resolvedStatePath) {
    $state = Get-Content $resolvedStatePath -Raw | ConvertFrom-Json
    $openPositions = @($state.open_positions.PSObject.Properties).Count
    $pending = @($state.pending_orders.PSObject.Properties)
    $pendingOrders = $pending.Count
    foreach ($entry in $pending) {
        $createdAt = To-DateTimeOrNull $entry.Value.created_at
        if ($null -ne $createdAt -and $createdAt -lt ([datetimeoffset]::UtcNow.AddHours(-1 * $StalePendingHours))) {
            $stalePending += 1
        }
    }
    if ([string]$state.status -ne "running") {
        $issues.Add("runtime_not_running")
    }
    if ([string]$state.halt_reason -ne "none") {
        $issues.Add("runtime_halted")
    }
    if ($state.PSObject.Properties.Name -contains "consecutive_data_failures" -and [int]$state.consecutive_data_failures -gt 0) {
        $issues.Add("data_source_failure")
    }
    if ($state.PSObject.Properties.Name -contains "last_data_error" -and -not [string]::IsNullOrWhiteSpace([string]$state.last_data_error)) {
        $issues.Add("last_data_error")
    }
    if ($stalePending -gt 0) {
        $issues.Add("stale_pending_orders")
    }
} else {
    $issues.Add("state_missing")
}

if ($tracebacks -gt 0) {
    $issues.Add("tracebacks_in_log")
}
if ($exitCodes -gt 0) {
    $issues.Add("nonzero_paper_runs")
}

$reportLines = @()
$reportLines += "# Paper Health Report"
$reportLines += ""
$reportLines += "- generated_at: $(Get-Date -Format o)"
$reportLines += "- repo: $repoRoot"
$reportLines += "- paper_days_observed: $paperDays"
$reportLines += "- complete_samples_observed: $completeSamples"
$reportLines += "- last_run_start: $(if ($null -ne $lastRunStart) { $lastRunStart.ToString('o') } else { '' })"
$reportLines += "- last_run_end: $(if ($null -ne $lastRunEnd) { $lastRunEnd.ToString('o') } else { '' })"
$reportLines += "- tracebacks_in_log: $tracebacks"
$reportLines += "- nonzero_paper_runs: $exitCodes"
$reportLines += ""
$reportLines += "## Runtime"
$reportLines += ""
if ($null -eq $state) {
    $reportLines += "- state: missing"
} else {
    $reportLines += "- status: $($state.status)"
    $reportLines += "- halt_reason: $($state.halt_reason)"
    $reportLines += "- orders_today: $($state.orders_today)"
    $reportLines += "- open_positions: $openPositions"
    $reportLines += "- pending_orders: $pendingOrders"
    if ($state.PSObject.Properties.Name -contains "last_data_success_at") {
        $reportLines += "- last_data_success_at: $($state.last_data_success_at)"
    }
    if ($state.PSObject.Properties.Name -contains "last_data_error") {
        $reportLines += "- last_data_error: $($state.last_data_error)"
    }
    if ($state.PSObject.Properties.Name -contains "consecutive_data_failures") {
        $reportLines += "- consecutive_data_failures: $($state.consecutive_data_failures)"
    }
    $reportLines += "- stale_pending_orders(>${StalePendingHours}h): $stalePending"
}
$reportLines += ""
$reportLines += "## Issues"
$reportLines += ""
if ($issues.Count -eq 0) {
    $reportLines += "- none"
} else {
    foreach ($issue in ($issues | Sort-Object -Unique)) {
        $reportLines += "- $issue"
    }
}

Set-Content -Path $resolvedReportPath -Value $reportLines -Encoding UTF8
Get-Content $resolvedReportPath
