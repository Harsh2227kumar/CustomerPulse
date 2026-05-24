[CmdletBinding()]
param(
    [switch]$Live,
    [string]$BaseUrl = "http://localhost:8000"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Invoke-Check {
    param(
        [Parameter(Mandatory)]
        [string]$Name,
        [Parameter(Mandatory)]
        [scriptblock]$Check
    )

    Write-Host ""
    Write-Host "== $Name =="
    & $Check
}

Invoke-Check "Backend unit and contract tests" {
    & (Join-Path $PSScriptRoot "backend\run-unit.ps1")
}

Invoke-Check "Infrastructure configuration checks" {
    & (Join-Path $PSScriptRoot "infra\verify-compose.ps1")
}

Invoke-Check "Frontend readiness checks" {
    & (Join-Path $PSScriptRoot "frontend\verify-frontend.ps1")
}

if ($Live) {
    Invoke-Check "Running backend API smoke checks" {
        & (Join-Path $PSScriptRoot "backend\run-live-smoke.ps1") -BaseUrl $BaseUrl
    }
}
else {
    Write-Host ""
    Write-Host "Live API checks skipped. Re-run with -Live after starting the configured backend."
}

Write-Host ""
Write-Host "CustomerPulse verification completed successfully."
