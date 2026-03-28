param(
    [string]$StatePath = "data/runtime/runtime_state.paper-supervisor.current.json",
    [string]$LogPath = "data/runtime/paper-supervisor.current.log",
    [string]$EventPath = "data/runtime/paper-events.current.jsonl",
    [string]$MetricsPath = "data/runtime/paper-metrics.latest.json",
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

function Add-CounterValue {
    param(
        [hashtable]$Counter,
        [string]$Key
    )
    if ([string]::IsNullOrWhiteSpace($Key)) {
        return
    }
    if ($Counter.ContainsKey($Key)) {
        $Counter[$Key] += 1
    } else {
        $Counter[$Key] = 1
    }
}

function Format-TopCounterLines {
    param(
        [hashtable]$Counter,
        [int]$Limit = 5
    )
    if ($Counter.Count -eq 0) {
        return @("- none")
    }
    return @(
        $Counter.GetEnumerator() |
            Sort-Object -Property @{ Expression = "Value"; Descending = $true }, @{ Expression = "Name"; Descending = $false } |
            Select-Object -First $Limit |
            ForEach-Object { "- $($_.Name): $($_.Value)" }
    )
}

function Get-SafeRatio {
    param(
        [double]$Numerator,
        [double]$Denominator
    )
    if ($Denominator -le 0) {
        return 0.0
    }
    return $Numerator / $Denominator
}

$resolvedStatePath = Resolve-ManagedPath $StatePath
$resolvedLogPath = Resolve-ManagedPath $LogPath
$resolvedEventPath = Resolve-ManagedPath $EventPath
$resolvedMetricsPath = Resolve-ManagedPath $MetricsPath
$resolvedReportPath = Resolve-ManagedPath $ReportPath
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $resolvedReportPath) | Out-Null

$issues = New-Object System.Collections.Generic.List[string]
$paperDays = 0
$completeSamples = 0
$tracebacks = 0
$exitCodes = 0
$lastRunStart = $null
$lastRunEnd = $null
$signalsGenerated = 0
$signalsRejected = 0
$ordersSubmitted = 0
$ordersRejected = 0
$ordersFilled = 0
$ordersPartiallyFilled = 0
$ordersExpired = 0
$ordersCanceled = 0
$tradesClosed = 0
$fillRate = 0.0
$cancelRate = 0.0
$avgFillAgeMs = 0.0
$avgFillPriceVsMidBps = 0.0
$makerFillShare = 0.0
$takerFillShare = 0.0
$marketDataFailures = 0
$marketDataRecoveries = 0
$eventCounts = @{}
$rejectionReasons = @{}
$fillSources = @{}
$dominantRejectionReason = $null
$dominantRejectionCount = 0
$capacityBoundRejectionCount = 0
$capacityBoundRejectionRatio = 0.0
$rejectedRatio = 0.0
$expiredOrCanceledRatio = 0.0
$baselineClassification = "capacity-bound"
$fillsObserved = 0
$zeroFillWithSubmissions = $false
$capacityBoundReasons = @(
    "daily order hard limit reached",
    "daily order soft limit reached",
    "max concurrent positions reached",
    "market already has a pending order",
    "max open orders reached"
)

if (Test-Path $resolvedLogPath) {
    $logLines = Get-Content $resolvedLogPath
    $runStartMatches = @($logLines | Where-Object { $_ -match '^=== run_start ' })
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

if (Test-Path $resolvedMetricsPath) {
    $metrics = Get-Content $resolvedMetricsPath -Raw | ConvertFrom-Json
    $paperDays = [int]$metrics.paper_days_observed
    $completeSamples = [int]$metrics.processed_snapshots
    $signalsGenerated = [int]$metrics.signals_generated
    $signalsRejected = [int]$metrics.signals_rejected
    $ordersSubmitted = [int]$metrics.orders_submitted
    $ordersRejected = [int]$metrics.orders_rejected
    $ordersFilled = [int]$metrics.orders_filled
    $ordersPartiallyFilled = [int]$metrics.orders_partially_filled
    $ordersExpired = [int]$metrics.orders_expired
    $ordersCanceled = [int]$metrics.orders_canceled
    $tradesClosed = [int]$metrics.trades_closed
    $fillRate = [double]$metrics.fill_rate
    $cancelRate = [double]$metrics.cancel_rate
    $avgFillAgeMs = [double]$metrics.avg_time_to_fill_ms
    $avgFillPriceVsMidBps = [double]$metrics.avg_fill_price_vs_mid_bps
    $makerFillShare = [double]$metrics.maker_fill_share
    $takerFillShare = [double]$metrics.taker_fill_share
    $marketDataFailures = [int]$metrics.market_data_failures
    $marketDataRecoveries = [int]$metrics.market_data_recoveries
} else {
    $issues.Add("metrics_missing")
}

if (Test-Path $resolvedEventPath) {
    foreach ($rawLine in Get-Content $resolvedEventPath) {
        $line = $rawLine.Trim()
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }
        $event = $line | ConvertFrom-Json
        $eventType = [string]$event.event_type
        if ([string]::IsNullOrWhiteSpace($eventType)) {
            continue
        }
        Add-CounterValue -Counter $eventCounts -Key $eventType
        $payload = $event.payload
        if ($eventType -eq "order.rejected" -and $null -ne $payload) {
            Add-CounterValue -Counter $rejectionReasons -Key ([string]$payload.reason)
        } elseif (($eventType -eq "order.filled" -or $eventType -eq "order.partially_filled") -and $null -ne $payload) {
            $fillSource = [string]$payload.fill_source
            if ([string]::IsNullOrWhiteSpace($fillSource)) {
                $fillSource = "unknown"
            }
            Add-CounterValue -Counter $fillSources -Key $fillSource
        }
    }
} else {
    $issues.Add("event_log_missing")
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

$fillsObserved = $ordersFilled + $ordersPartiallyFilled
$zeroFillWithSubmissions = $ordersSubmitted -gt 0 -and $fillsObserved -eq 0
$rejectedRatio = Get-SafeRatio -Numerator $ordersRejected -Denominator ($ordersRejected + $ordersSubmitted)
$expiredOrCanceledRatio = Get-SafeRatio -Numerator ($ordersExpired + $ordersCanceled) -Denominator $ordersSubmitted

if ($rejectionReasons.Count -gt 0) {
    $dominantReason = $rejectionReasons.GetEnumerator() |
        Sort-Object -Property @{ Expression = "Value"; Descending = $true }, @{ Expression = "Name"; Descending = $false } |
        Select-Object -First 1
    if ($null -ne $dominantReason) {
        $dominantRejectionReason = [string]$dominantReason.Name
        $dominantRejectionCount = [int]$dominantReason.Value
    }
    foreach ($reason in $capacityBoundReasons) {
        if ($rejectionReasons.ContainsKey($reason)) {
            $capacityBoundRejectionCount += [int]$rejectionReasons[$reason]
        }
    }
    $capacityBoundRejectionRatio = Get-SafeRatio -Numerator $capacityBoundRejectionCount -Denominator $ordersRejected
}

$submissionRate = Get-SafeRatio -Numerator $ordersSubmitted -Denominator $signalsGenerated
if (
    $signalsGenerated -ge 100 `
    -and $ordersRejected -ge [Math]::Max($ordersSubmitted * 5, 25) `
    -and $capacityBoundRejectionRatio -ge 0.5 `
    -and $submissionRate -le 0.05
) {
    $baselineClassification = "capacity-bound"
} elseif ($marketDataFailures -gt 0 -and $ordersSubmitted -eq 0 -and $fillsObserved -eq 0) {
    $baselineClassification = "data-bound"
} elseif ($ordersSubmitted -gt 0 -and $fillsObserved -le [Math]::Max(1, [int]($ordersSubmitted / 10)) -and ($ordersExpired + $ordersCanceled) -ge [Math]::Max(1, [int]($ordersSubmitted / 2))) {
    $baselineClassification = "execution-bound"
} elseif ($tradesClosed -gt 0) {
    $baselineClassification = "alpha-bound"
} elseif ($marketDataFailures -gt 0 -and $capacityBoundRejectionRatio -lt 0.25) {
    $baselineClassification = "data-bound"
} elseif ($fillsObserved -gt 0 -and $tradesClosed -gt 0) {
    $baselineClassification = "alpha-bound"
} elseif ($ordersSubmitted -gt 0) {
    $baselineClassification = "execution-bound"
}

if ($zeroFillWithSubmissions) {
    $issues.Add("zero_fill_with_submissions")
}
if ($capacityBoundRejectionRatio -ge 0.5 -and $ordersRejected -ge [Math]::Max($ordersSubmitted, 3)) {
    $issues.Add("capacity_bound_rejections")
}
if ($expiredOrCanceledRatio -ge 0.5 -and $zeroFillWithSubmissions) {
    $issues.Add("expiry_heavy")
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
$reportLines += "## Diagnostics"
$reportLines += ""
$reportLines += "- baseline_classification: $baselineClassification"
$reportLines += "- event_log_path: $resolvedEventPath"
$reportLines += "- zero_fill_with_submissions: $($zeroFillWithSubmissions.ToString().ToLowerInvariant())"
$reportLines += "- rejected_ratio: $([string]::Format('{0:N4}', $rejectedRatio))"
$reportLines += "- expired_or_canceled_ratio: $([string]::Format('{0:N4}', $expiredOrCanceledRatio))"
$reportLines += "- capacity_bound_rejection_ratio: $([string]::Format('{0:N4}', $capacityBoundRejectionRatio))"
$reportLines += "- dominant_rejection_reason: $(if ($null -ne $dominantRejectionReason) { $dominantRejectionReason } else { '' })"
$reportLines += "- dominant_rejection_count: $dominantRejectionCount"
$reportLines += ""
$reportLines += "### Top Rejection Reasons"
$reportLines += ""
$reportLines += Format-TopCounterLines -Counter $rejectionReasons
$reportLines += ""
$reportLines += "### Fill Sources"
$reportLines += ""
$reportLines += Format-TopCounterLines -Counter $fillSources
$reportLines += ""
$reportLines += "## Execution"
$reportLines += ""
$reportLines += "- signals_generated: $signalsGenerated"
$reportLines += "- signals_rejected: $signalsRejected"
$reportLines += "- orders_submitted: $ordersSubmitted"
$reportLines += "- orders_rejected: $ordersRejected"
$reportLines += "- orders_filled: $ordersFilled"
$reportLines += "- orders_partially_filled: $ordersPartiallyFilled"
$reportLines += "- orders_expired: $ordersExpired"
$reportLines += "- orders_canceled: $ordersCanceled"
$reportLines += "- trades_closed: $tradesClosed"
$reportLines += "- fill_rate: $([string]::Format('{0:N4}', $fillRate))"
$reportLines += "- cancel_rate: $([string]::Format('{0:N4}', $cancelRate))"
$reportLines += "- avg_time_to_fill_ms: $([string]::Format('{0:N2}', $avgFillAgeMs))"
$reportLines += "- avg_fill_price_vs_mid_bps: $([string]::Format('{0:N2}', $avgFillPriceVsMidBps))"
$reportLines += "- maker_fill_share: $([string]::Format('{0:N4}', $makerFillShare))"
$reportLines += "- taker_fill_share: $([string]::Format('{0:N4}', $takerFillShare))"
$reportLines += "- market_data_failures: $marketDataFailures"
$reportLines += "- market_data_recoveries: $marketDataRecoveries"
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
