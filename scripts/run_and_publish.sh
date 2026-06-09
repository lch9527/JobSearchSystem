#!/usr/bin/env bash
set -u

project_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$project_dir"

"$project_dir/.venv/bin/python" "$project_dir/main.py"
run_status=$?

# Exit 1 means one or more sources failed, but main.py still refreshed local outputs.
if (( run_status <= 1 )); then
    "$project_dir/scripts/publish_website.sh"
    publish_status=$?
    if (( publish_status != 0 )); then
        exit "$publish_status"
    fi
fi

exit "$run_status"
