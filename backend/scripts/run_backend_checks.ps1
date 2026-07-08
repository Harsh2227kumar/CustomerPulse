param(
    [switch]$SkipEmbedding,
    [switch]$SkipCompose
)

$ErrorActionPreference = "Stop"

$BackendDir = Split-Path -Parent $PSScriptRoot
$RepoDir = Split-Path -Parent $BackendDir

Set-Location $BackendDir
$env:PYTHONPATH = "."

python -m unittest discover -s tests -p "test_*.py" -v
if (-not $SkipEmbedding) {
    python scripts\download_embedding_model.py --model all-MiniLM-L6-v2 --local-files-only
}
python -m app.db.setup --help

if (-not $SkipCompose) {
    Set-Location $RepoDir
    docker compose config --quiet
}
