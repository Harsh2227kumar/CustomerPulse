[CmdletBinding()]
param(
    [string]$BaseUrl = "http://localhost:8000"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$rootUrl = $BaseUrl.TrimEnd("/")
$healthUrl = "$rootUrl/api/health"
$openApiUrl = "$rootUrl/openapi.json"

try {
    $health = Invoke-RestMethod -Method Get -Uri $healthUrl -TimeoutSec 10
}
catch {
    throw "Cannot reach the backend health endpoint at $healthUrl. Start the configured service first. $($_.Exception.Message)"
}

if ($health.status -ne "ok") {
    throw "The backend health response did not report status=ok."
}

$openApi = Invoke-RestMethod -Method Get -Uri $openApiUrl -TimeoutSec 10
$expectedPaths = @(
    "/api/health",
    "/api/complaints",
    "/api/process",
    "/api/ingestion/s3/options"
)
$availablePaths = @($openApi.paths.PSObject.Properties.Name)

foreach ($path in $expectedPaths) {
    if ($availablePaths -notcontains $path) {
        throw "The live OpenAPI document is missing expected endpoint $path."
    }
}

Write-Host "PASS: $healthUrl returned status=ok."
Write-Host "PASS: Expected REST API endpoints are advertised by $openApiUrl."
Write-Host "INFO: A normally started backend reaches this state only after startup database and Bedrock checks pass."
