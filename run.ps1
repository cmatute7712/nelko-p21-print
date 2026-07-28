$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
$VenvPath = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"

if (-not (Test-Path -LiteralPath $VenvPython)) {
    Write-Host "Creating Python virtual environment..."
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -m venv $VenvPath
    }
    elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv $VenvPath
    }
    else {
        throw "Python 3 was not found. Install Python 3.9 or newer and try again."
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the Python virtual environment."
    }
}

Write-Host "Installing project requirements..."
& $VenvPython -m pip install --disable-pip-version-check -r (Join-Path $ProjectRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    throw "Could not install the project requirements."
}

& $VenvPython (Join-Path $ProjectRoot "p21_print.py") @args
exit $LASTEXITCODE
