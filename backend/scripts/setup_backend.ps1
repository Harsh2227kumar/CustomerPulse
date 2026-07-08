param(
    [switch]$SkipBedrock,
    [switch]$VerifyEmbedding
)

$ErrorActionPreference = "Stop"

$BackendDir = Split-Path -Parent $PSScriptRoot
Set-Location $BackendDir

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

$env:PYTHONPATH = "."

$setupArgs = @("--yes")
if ($SkipBedrock) {
    $setupArgs += "--skip-bedrock"
}
if ($VerifyEmbedding) {
    $setupArgs += "--verify-embedding"
}

& .\.venv\Scripts\python.exe -m app.db.setup @setupArgs
