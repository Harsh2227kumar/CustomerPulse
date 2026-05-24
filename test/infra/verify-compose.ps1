[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$composePath = Join-Path $repoRoot "docker-compose.yml"
$templatePath = Join-Path $repoRoot ".env.template"

if (-not (Test-Path $composePath)) {
    throw "Missing Docker Compose configuration: $composePath"
}

& docker compose -f $composePath config --quiet
if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose configuration validation failed."
}

$composeConfig = (& docker compose -f $composePath config) -join "`n"
if ($LASTEXITCODE -ne 0) {
    throw "Unable to render Docker Compose configuration."
}

foreach ($fragment in @("customerpulse-backend", "/api/health")) {
    if ($composeConfig -notmatch [regex]::Escape($fragment)) {
        throw "Docker Compose configuration does not include expected backend fragment: $fragment"
    }
}

if (-not (Test-Path $templatePath)) {
    throw "Missing environment variable template: $templatePath"
}

$template = Get-Content -Raw $templatePath
foreach ($requiredVariable in @("DATABASE_URL=", "BEDROCK_API_KEY=", "S3_BUCKET_NAME=", "CFPB_S3_KEY=")) {
    if ($template -notmatch [regex]::Escape($requiredVariable)) {
        throw ".env.template is missing required variable $requiredVariable"
    }
}

Write-Host "PASS: Docker Compose is valid and declares backend health checking."
Write-Host "PASS: .env.template declares database, Bedrock, and S3 configuration inputs."
