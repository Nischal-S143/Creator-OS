# Runs every backend check. Exits non-zero on the first failure. Run from anywhere.
# Failures are detected by exit code: Windows PowerShell treats any tool's stderr output as an error.
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$bin = Join-Path $root ".venv\Scripts"

function Step($name, [scriptblock]$command) {
    Write-Output "--- $name"
    & $command
    if ($LASTEXITCODE -ne 0) { throw "$name failed" }
}

Push-Location (Join-Path $root "apps\api")
try {
    Step "lint" { & "$bin\ruff.exe" check . }
    Step "format" { & "$bin\ruff.exe" format --check . }
    Step "security scan" { & "$bin\bandit.exe" -q -r app alembic scripts --severity-level medium }
    Step "dependency audit" { & "$bin\pip-audit.exe" -r requirements.lock --no-deps --disable-pip }
    Step "tests" { & "$bin\python.exe" -m pytest -q }
}
finally {
    Pop-Location
}
Write-Output "All checks passed"
