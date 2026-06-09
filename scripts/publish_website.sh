#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$project_dir"

export GIT_TERMINAL_PROMPT=0

if ! git diff --quiet -- . ':(exclude)docs/jobs.json' || \
   ! git diff --cached --quiet -- . ':(exclude)docs/jobs.json'; then
    echo "Website publish skipped: unrelated tracked changes are present." >&2
    exit 1
fi

git add -- docs/jobs.json
if git diff --cached --quiet -- docs/jobs.json; then
    echo "Website publish skipped: docs/jobs.json is unchanged."
    exit 0
fi

run_time=$(date --iso-8601=seconds)
git commit -m "Update job results ${run_time}"

if ! timeout 60 git push origin main; then
    echo "Initial push failed; synchronizing with origin/main and retrying." >&2
    timeout 60 git pull --rebase origin main
    timeout 60 git push origin main
fi

echo "Website results published at ${run_time}."
