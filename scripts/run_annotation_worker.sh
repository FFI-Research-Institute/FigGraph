#!/usr/bin/env bash
set -euo pipefail

script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
repo_dir="$(dirname -- "$script_dir")"
budget="${FIGRAPH_ANNOTATION_BUDGET:-100}"
python_bin="${FIGRAPH_ANNOTATION_PYTHON:-$repo_dir/.venv/bin/python}"

if [[ ! -x "$python_bin" ]]; then
  python_bin="python3"
fi

cd "$repo_dir"
exec "$python_bin" -m figraph.cli annotate --budget "$budget"
