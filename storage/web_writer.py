from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from storage.db import Database


PUBLIC_JOB_FIELDS = (
    "job_hash",
    "title",
    "company",
    "location",
    "url",
    "source_name",
    "source_type",
    "salary",
    "employment_type",
    "date_posted",
    "date_found",
    "last_seen",
    "status",
    "match_score",
    "match_reason",
)


def export_website(database: Database, output_dir: Path, minimum_score: int = 35) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    jobs = database.list_jobs(minimum_score)
    public_jobs = [
        {field: job.get(field) or "" for field in PUBLIC_JOB_FIELDS}
        for job in jobs
    ]
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    payload: dict[str, Any] = {
        "generated_at": generated_at,
        "minimum_score": minimum_score,
        "total": len(public_jobs),
        "jobs": public_jobs,
    }
    destination = output_dir / "jobs.json"
    temporary = output_dir / ".jobs.json.tmp"
    temporary.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8"
    )
    temporary.replace(destination)
    return destination
