[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$backendRoot = Join-Path $repoRoot "backend"
$existingPythonPath = $env:PYTHONPATH
$existingDontWriteByteCode = $env:PYTHONDONTWRITEBYTECODE

try {
    $env:PYTHONDONTWRITEBYTECODE = "1"
    if ([string]::IsNullOrWhiteSpace($existingPythonPath)) {
        $env:PYTHONPATH = $backendRoot
    }
    else {
        $env:PYTHONPATH = "$backendRoot;$existingPythonPath"
    }

    Push-Location $repoRoot
    try {
        Write-Host "Running existing backend ingestion tests..."
        & python -m unittest discover -s (Join-Path $backendRoot "tests") -p "test_*.py" -v
        if ($LASTEXITCODE -ne 0) {
            throw "Existing backend tests failed."
        }

        Write-Host ""
        Write-Host "Running root backend contract tests..."
        & python -m unittest discover -s $PSScriptRoot -p "test_*.py" -v
        if ($LASTEXITCODE -ne 0) {
            throw "Root backend contract tests failed."
        }
    }
    finally {
        Pop-Location
    }
}
finally {
    $env:PYTHONPATH = $existingPythonPath
    $env:PYTHONDONTWRITEBYTECODE = $existingDontWriteByteCode
}
