[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$frontendRoot = Join-Path $repoRoot "frontend"
$packagePath = Join-Path $frontendRoot "package.json"

if (-not (Test-Path $frontendRoot)) {
    Write-Host "SKIP: No frontend directory is present in this repository."
    return
}

if (-not (Test-Path $packagePath)) {
    $sourceExtensions = @(".css", ".html", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte")
    $sourceFiles = @(
        @(
            Get-ChildItem -Path $frontendRoot -File -ErrorAction SilentlyContinue
            foreach ($sourceDirectory in @("src", "app", "pages", "public")) {
                $path = Join-Path $frontendRoot $sourceDirectory
                if (Test-Path $path) {
                    Get-ChildItem -Path $path -Recurse -File -ErrorAction SilentlyContinue
                }
            }
        ) | Where-Object { $sourceExtensions -contains $_.Extension.ToLowerInvariant() }
    )

    if ($sourceFiles.Count -eq 0) {
        Write-Host "SKIP: frontend exists but currently has no runnable source files or package.json."
        return
    }
    throw "Frontend source files exist, but frontend/package.json is missing."
}

$package = Get-Content -Raw $packagePath | ConvertFrom-Json
if (-not $package.scripts.build) {
    throw "frontend/package.json must provide a build script for verification."
}

Push-Location $frontendRoot
try {
    & npm run build
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend build failed."
    }

    if ($package.scripts.test -and $package.scripts.test -match "vitest") {
        & npm run test -- --run
        if ($LASTEXITCODE -ne 0) {
            throw "Frontend Vitest suite failed."
        }
    }
    elseif ($package.scripts.test) {
        Write-Host "INFO: A frontend test script exists; add its non-watching CI command to this verifier when the frontend is checked in."
    }
}
finally {
    Pop-Location
}

Write-Host "PASS: Frontend build verification succeeded."
