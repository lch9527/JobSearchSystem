from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from collectors.base import Job
from storage.models import ALLOWED_STATUSES
from utils.text import normalize_url


SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_hash TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    url TEXT,
    source_name TEXT,
    source_type TEXT,
    description TEXT,
    salary TEXT,
    employment_type TEXT,
    date_posted TEXT,
    date_found TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'New',
    match_score INTEGER DEFAULT 0,
    match_reason TEXT,
    notes TEXT,
    raw_data TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(match_score);
CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);
CREATE INDEX IF NOT EXISTS idx_jobs_last_seen ON jobs(last_seen);
CREATE INDEX IF NOT EXISTS idx_jobs_url ON jobs(url);

CREATE TABLE IF NOT EXISTS run_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_time TEXT NOT NULL,
    sources_checked INTEGER NOT NULL,
    jobs_found INTEGER NOT NULL,
    new_jobs_added INTEGER NOT NULL,
    errors TEXT,
    duration_seconds REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS source_checks (
    source_name TEXT PRIMARY KEY,
    last_checked TEXT NOT NULL,
    last_result TEXT,
    updated_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.connection = sqlite3.connect(path, timeout=30)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript(SCHEMA)
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def upsert_job(self, job: Job, now: str | None = None) -> bool:
        timestamp = now or datetime.now().astimezone().isoformat(timespec="seconds")
        normalized_url = normalize_url(job.url)
        existing = self.connection.execute(
            "SELECT id, job_hash FROM jobs WHERE job_hash = ?",
            (job.job_hash,),
        ).fetchone()
        if existing is None and normalized_url:
            existing = self.connection.execute(
                "SELECT id, job_hash FROM jobs WHERE url = ?", (normalized_url,)
            ).fetchone()

        values = (
            job.title,
            job.company,
            job.location,
            normalized_url,
            job.source_name,
            job.source_type,
            job.description,
            job.salary,
            job.employment_type,
            job.date_posted,
            timestamp,
            job.match_score,
            job.match_reason,
            json.dumps(job.raw_data, ensure_ascii=True, default=str),
            timestamp,
        )
        if existing:
            job.job_hash = existing["job_hash"]
            self.connection.execute(
                """
                UPDATE jobs SET
                    title = ?, company = ?, location = ?, url = ?,
                    source_name = ?, source_type = ?, description = ?,
                    salary = ?, employment_type = ?, date_posted = ?,
                    last_seen = ?, match_score = ?, match_reason = ?,
                    raw_data = ?, updated_at = ?
                WHERE id = ?
                """,
                (*values, existing["id"]),
            )
            self.connection.commit()
            return False

        self.connection.execute(
            """
            INSERT INTO jobs (
                job_hash, title, company, location, url, source_name,
                source_type, description, salary, employment_type,
                date_posted, date_found, last_seen, status, match_score,
                match_reason, notes, raw_data, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'New', ?, ?, '', ?, ?, ?)
            """,
            (
                job.job_hash,
                job.title,
                job.company,
                job.location,
                normalized_url,
                job.source_name,
                job.source_type,
                job.description,
                job.salary,
                job.employment_type,
                job.date_posted,
                timestamp,
                timestamp,
                job.match_score,
                job.match_reason,
                json.dumps(job.raw_data, ensure_ascii=True, default=str),
                timestamp,
                timestamp,
            ),
        )
        self.connection.commit()
        return True

    def update_manual_fields(
        self, job_hash: str | None, url: str | None, status: str, notes: str
    ) -> bool:
        if status not in ALLOWED_STATUSES:
            return False
        timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
        if job_hash:
            cursor = self.connection.execute(
                """
                UPDATE jobs SET status = ?, notes = ?, updated_at = ?
                WHERE job_hash = ?
                """,
                (status, notes, timestamp, job_hash),
            )
        elif url:
            cursor = self.connection.execute(
                """
                UPDATE jobs SET status = ?, notes = ?, updated_at = ?
                WHERE url = ?
                """,
                (status, notes, timestamp, normalize_url(url)),
            )
        else:
            return False
        self.connection.commit()
        return cursor.rowcount > 0

    def list_jobs(self, minimum_score: int = 0) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT * FROM jobs
            WHERE match_score >= ?
            ORDER BY
                CASE status
                    WHEN 'New' THEN 1
                    WHEN 'Interested' THEN 2
                    WHEN 'Applied' THEN 3
                    WHEN 'Not Match' THEN 4
                    WHEN 'Rejected' THEN 5
                    WHEN 'Archived' THEN 6
                    ELSE 7
                END,
                match_score DESC,
                date_found DESC
            """,
            (minimum_score,),
        ).fetchall()
        return [dict(row) for row in rows]

    def status_counts(self) -> dict[str, int]:
        rows = self.connection.execute(
            "SELECT status, COUNT(*) AS count FROM jobs GROUP BY status"
        ).fetchall()
        counts = {status: 0 for status in ALLOWED_STATUSES}
        counts.update({row["status"]: row["count"] for row in rows})
        counts["Total"] = self.connection.execute(
            "SELECT COUNT(*) FROM jobs"
        ).fetchone()[0]
        return counts

    def add_run_log(self, stats: dict[str, Any]) -> None:
        self.connection.execute(
            """
            INSERT INTO run_logs (
                run_time, sources_checked, jobs_found, new_jobs_added,
                errors, duration_seconds
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                stats["run_time"],
                stats["sources_checked"],
                stats["jobs_found"],
                stats["new_jobs_added"],
                "\n".join(stats.get("errors", [])),
                stats["duration_seconds"],
            ),
        )
        self.connection.commit()

    def delete_jobs_containing(self, text: str) -> int:
        pattern = f"%{text}%"
        cursor = self.connection.execute(
            """
            DELETE FROM jobs
            WHERE title LIKE ? OR description LIKE ? OR match_reason LIKE ?
            """,
            (pattern, pattern, pattern),
        )
        self.connection.commit()
        return cursor.rowcount

    def list_run_logs(self, limit: int = 200) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM run_logs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def record_source_check(self, name: str, result: str, now: str) -> None:
        self.connection.execute(
            """
            INSERT INTO source_checks (source_name, last_checked, last_result, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(source_name) DO UPDATE SET
                last_checked = excluded.last_checked,
                last_result = excluded.last_result,
                updated_at = excluded.updated_at
            """,
            (name, now, result, now),
        )
        self.connection.commit()

    def source_checks(self) -> dict[str, dict[str, Any]]:
        rows = self.connection.execute("SELECT * FROM source_checks").fetchall()
        return {row["source_name"]: dict(row) for row in rows}

