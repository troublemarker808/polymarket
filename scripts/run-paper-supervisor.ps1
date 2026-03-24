param(
    [string]$ConfigDir = "configs",
    [string]$StatePath = "data/runtime/runtime_state.paper-supervisor.current.json",
    [string]$LogPath = "data/runtime/paper-supervisor.current.log",
    [string]$PidPath = "data/runtime/paper-supervisor.current.pid",
    [int]$Limit = 50,
    [int]$MaxPages = 1,
    [int]$IntervalSeconds = 300,
    [int]$MaxCycles = 0
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

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $resolvedStatePath) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $resolvedLogPath) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $resolvedPidPath) | Out-Null

Set-Content -Path $resolvedPidPath -Value "$PID" -Encoding ASCII
Write-RunLog -ResolvedLogPath $resolvedLogPath -Message "=== supervisor_start $(Get-Date -Format o)"

$cycle = 0
while ($true) {
    if ($MaxCycles -gt 0 -and $cycle -ge $MaxCycles) {
        break
    }

    $cycle += 1
    Write-RunLog -ResolvedLogPath $resolvedLogPath -Message "=== run_start $(Get-Date -Format o)"
    $output = & python -m pm_bot paper-crypto-once --config-dir $ConfigDir --limit $Limit --max-pages $MaxPages --state-path $resolvedStatePath 2>&1
    foreach ($line in $output) {
        Write-RunLog -ResolvedLogPath $resolvedLogPath -Message ([string]$line)
    }

    if ($LASTEXITCODE -ne 0) {
        Write-RunLog -ResolvedLogPath $resolvedLogPath -Message "exit_code=$LASTEXITCODE"
        Write-RunLog -ResolvedLogPath $resolvedLogPath -Message "issue=paper_command_failed"
    }

    Write-RunLog -ResolvedLogPath $resolvedLogPath -Message "=== run_end $(Get-Date -Format o)"

    if ($MaxCycles -gt 0 -and $cycle -ge $MaxCycles) {
        break
    }

    Start-Sleep -Seconds $IntervalSeconds
}

Write-RunLog -ResolvedLogPath $resolvedLogPath -Message "=== supervisor_exit $(Get-Date -Format o)"
