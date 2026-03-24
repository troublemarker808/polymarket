param(
    [string]$ConfigDir = "configs",
    [string]$StatePath = "data/runtime/runtime_state.paper-supervisor.current.json",
    [string]$LogPath = "data/runtime/paper-supervisor.current.log",
    [string]$PidPath = "data/runtime/paper-supervisor.current.pid",
    [string]$HealthCheckScriptPath = "scripts/check-paper-health.ps1",
    [string]$HealthReportPath = "data/runtime/paper-health.latest.md",
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

function Format-ProcessArgument {
    param([string]$Value)
    if ($null -eq $Value) {
        return '""'
    }
    return '"' + ($Value -replace '(\\*)"', '$1$1\"') + '"'
}

function Invoke-PaperRun {
    param(
        [string]$ResolvedStatePath,
        [string]$ConfigDirValue,
        [int]$LimitValue,
        [int]$MaxPagesValue
    )

    $argumentValues = @(
        "-m",
        "pm_bot",
        "paper-crypto-once",
        "--config-dir",
        $ConfigDirValue,
        "--limit",
        "$LimitValue",
        "--max-pages",
        "$MaxPagesValue",
        "--state-path",
        $ResolvedStatePath
    )

    $stdoutPath = [System.IO.Path]::GetTempFileName()
    $stderrPath = [System.IO.Path]::GetTempFileName()
    try {
        $pythonCommand = @("python") + ($argumentValues | ForEach-Object { Format-ProcessArgument -Value ([string]$_) })
        $commandText = (($pythonCommand -join " ") + " 1>" + (Format-ProcessArgument -Value $stdoutPath) + " 2>" + (Format-ProcessArgument -Value $stderrPath))

        $startInfo = New-Object System.Diagnostics.ProcessStartInfo
        $startInfo.FileName = "cmd.exe"
        $startInfo.Arguments = "/d /c $commandText"
        $startInfo.UseShellExecute = $false
        $startInfo.CreateNoWindow = $true

        $process = New-Object System.Diagnostics.Process
        $process.StartInfo = $startInfo
        [void]$process.Start()
        $process.WaitForExit()

        $lines = @()
        foreach ($path in @($stdoutPath, $stderrPath)) {
            if (Test-Path $path) {
                $lines += Get-Content $path
            }
        }

        return @{
            Output = $lines
            ExitCode = $process.ExitCode
        }
    } finally {
        foreach ($path in @($stdoutPath, $stderrPath)) {
            if (Test-Path $path) {
                Remove-Item -Path $path -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

$resolvedStatePath = Resolve-ManagedPath $StatePath
$resolvedLogPath = Resolve-ManagedPath $LogPath
$resolvedPidPath = Resolve-ManagedPath $PidPath
$resolvedHealthCheckScriptPath = Resolve-ManagedPath $HealthCheckScriptPath
$resolvedHealthReportPath = Resolve-ManagedPath $HealthReportPath

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $resolvedStatePath) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $resolvedLogPath) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $resolvedPidPath) | Out-Null
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
    $paperRun = Invoke-PaperRun -ResolvedStatePath $resolvedStatePath -ConfigDirValue $ConfigDir -LimitValue $Limit -MaxPagesValue $MaxPages
    foreach ($line in $paperRun.Output) {
        Write-RunLog -ResolvedLogPath $resolvedLogPath -Message ([string]$line)
    }

    if ($paperRun.ExitCode -ne 0) {
        Write-RunLog -ResolvedLogPath $resolvedLogPath -Message "exit_code=$($paperRun.ExitCode)"
        Write-RunLog -ResolvedLogPath $resolvedLogPath -Message "issue=paper_command_failed"
    }

    Write-RunLog -ResolvedLogPath $resolvedLogPath -Message "=== run_end $(Get-Date -Format o)"
    if (Test-Path $resolvedHealthCheckScriptPath) {
        try {
            & $resolvedHealthCheckScriptPath -StatePath $resolvedStatePath -LogPath $resolvedLogPath -ReportPath $resolvedHealthReportPath | Out-Null
            $healthExitCodeVar = Get-Variable -Name LASTEXITCODE -ErrorAction SilentlyContinue
            if ($null -ne $healthExitCodeVar -and $healthExitCodeVar.Value -ne 0) {
                Write-RunLog -ResolvedLogPath $resolvedLogPath -Message "health_exit_code=$($healthExitCodeVar.Value)"
                Write-RunLog -ResolvedLogPath $resolvedLogPath -Message "issue=health_check_failed"
            }
        } catch {
            Write-RunLog -ResolvedLogPath $resolvedLogPath -Message "health_check_error=$($_.Exception.Message)"
            Write-RunLog -ResolvedLogPath $resolvedLogPath -Message "issue=health_check_failed"
        }
    } else {
        Write-RunLog -ResolvedLogPath $resolvedLogPath -Message "health_check_error=missing_script"
        Write-RunLog -ResolvedLogPath $resolvedLogPath -Message "issue=health_check_failed"
    }

    if ($MaxCycles -gt 0 -and $cycle -ge $MaxCycles) {
        break
    }

    Start-Sleep -Seconds $IntervalSeconds
}

Write-RunLog -ResolvedLogPath $resolvedLogPath -Message "=== supervisor_exit $(Get-Date -Format o)"
