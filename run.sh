#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
venv_path="$project_root/.venv"
venv_python="$venv_path/bin/python"

if [[ ! -x "$venv_python" ]]; then
    echo "Creating Python virtual environment..."
    if command -v python3 >/dev/null 2>&1; then
        python3 -m venv "$venv_path"
    elif command -v python >/dev/null 2>&1; then
        python -m venv "$venv_path"
    else
        echo "Python 3 was not found. Install Python 3.9 or newer and try again." >&2
        exit 1
    fi
fi

echo "Installing project requirements..."
"$venv_python" -m pip install --disable-pip-version-check -r "$project_root/requirements.txt"

exec "$venv_python" "$project_root/p21_print.py" "$@"
