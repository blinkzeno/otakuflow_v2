# Starts the Otakuflow backend from anywhere. Anchors to this folder.
Set-Location $PSScriptRoot
$ErrorActionPreference = "Stop"

# Needs Python 3.11 or newer on PATH (command py)
try {
  $pyVersion = py --version 2>&1
  Write-Host "Found $pyVersion"
} catch {
  Write-Host "Python is missing. Install Python 3.11 or newer, then run again."
  exit 1
}

if (-not (Test-Path ".venv")) {
  Write-Host "Creating virtual env..."
  py -m venv .venv
}

Write-Host "Installing backend requirements..."
.\.venv\Scripts\python -m pip install -r backend\requirements.txt

Write-Host "Starting API on http://127.0.0.1:8000 ..."
.\.venv\Scripts\python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
