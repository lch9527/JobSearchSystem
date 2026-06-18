from __future__ import annotations

import sys
import time
from datetime import datetime

from dateutil import parser as date_parser
from dotenv import load_dotenv

from collectors import create_collector
from collectors.base import Job
from matching.eligibility import CLEARANCE_EXCLUSION_PHRASE, is_eligible_job
from matching.scorer import EXPORT_CONTROL_PHRASE, score_job
from storage.db import Database
from storage.excel_writer import export_excel, import_manual_fields
from storage.web_writer import export_website
from utils.config import PROJECT_ROOT, apply_environment_overrides, load_yaml, resolve_path
from utils.hashing import create_job_hash
from utils.logging import setup_logging
from utils.rate_limiter import RateLimiter
from utils.text import clean_text, normalize_url


def normalize_job(job: Job) -> Job:
    job.title = clean_text(job.title)
    job.company = clean_text(job.company)
    job.location = clean_text(job.location)
    job.url = normalize_url(job.url)
    job.description = clean_text(job.description)
    job.salary = clean_text(job.salary)
    job.employment_type = clean_text(job.employment_type)
    job.date_posted = normalize_date(job.date_posted)
    job.job_hash = create_job_hash(job.title, job.company, job.url, job.location)
    return job


def normalize_date(value: str | int | float | None) -> str:
    if value in (None, ""):
        return ""
    try:
        if isinstance(value, (int, float)) or str(value).isdigit():
            numeric = float(value)
            if numeric > 10_000_000_000:
                numeric /= 1000
            return datetime.fromtimestamp(numeric).astimezone().isoformat(timespec="seconds")
        return date_parser.parse(str(value)).isoformat()
    except (ValueError, TypeError, OverflowError):
        return str(value)


def run() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    settings = apply_environment_overrides(load_yaml("config/settings.yaml"))
    sources = load_yaml("config/sources.yaml").get("sources", [])
    keywords = load_yaml("config/keywords.yaml")
    logger = setup_logging(
        resolve_path(settings.get("logging", {}).get("path", "logs/job_radar.log")),
        settings.get("logging", {}).get("level", "INFO"),
    )
    logger.info("Starting Job Radar run")

    started = time.monotonic()
    run_time = datetime.now().astimezone().isoformat(timespec="seconds")
    stats = {
        "run_time": run_time,
        "sources_checked": 0,
        "jobs_found": 0,
        "new_jobs_added": 0,
        "errors": [],
        "duration_seconds": 0.0,
    }
    database = Database(resolve_path(settings["database"]["path"]))
    excel_path = resolve_path(settings["excel"]["path"])

    try:
        imported = import_manual_fields(excel_path, database, logger)
        if imported:
            logger.info("Imported manual fields for %d jobs from Excel", imported)

        rate_limiter = RateLimiter(
            settings.get("requests", {}), settings.get("rate_limit", {})
        )
        for source in sources:
            if not source.get("enabled", False):
                continue
            source_name = source.get("name", "Unnamed source")
            stats["sources_checked"] += 1
            checked_at = datetime.now().astimezone().isoformat(timespec="seconds")
            try:
                collector = create_collector(
                    source, rate_limiter, settings.get("requests", {})
                )
                jobs = collector.fetch_jobs()
                stats["jobs_found"] += len(jobs)
                for job in jobs:
                    normalized = normalize_job(job)
                    if not is_eligible_job(normalized):
                        logger.info(
                            "Skipped ineligible job: %s - %s (%s)",
                            normalized.title,
                            normalized.company,
                            normalized.location,
                        )
                        continue
                    normalized.match_score, normalized.match_reason = score_job(
                        normalized, keywords
                    )
                    if database.upsert_job(normalized):
                        stats["new_jobs_added"] += 1
                        logger.info(
                            "Added new job: %s - %s", normalized.title, normalized.company
                        )
                database.record_source_check(
                    source_name, f"Success: {len(jobs)} jobs", checked_at
                )
                logger.info("Checked source: %s, found %d jobs", source_name, len(jobs))
            except Exception as exc:
                message = f"{source_name}: {type(exc).__name__}: {exc}"
                stats["errors"].append(message)
                database.record_source_check(source_name, message, checked_at)
                logger.exception("Source failed: %s", source_name)

        stats["duration_seconds"] = round(time.monotonic() - started, 2)
        database.add_run_log(stats)
        deleted_jobs = database.delete_jobs_containing(EXPORT_CONTROL_PHRASE)
        if deleted_jobs:
            logger.info("Deleted %d jobs that matched the export-control exclusion", deleted_jobs)
        deleted_clearance_jobs = database.delete_jobs_containing(CLEARANCE_EXCLUSION_PHRASE)
        if deleted_clearance_jobs:
            logger.info(
                "Deleted %d jobs that matched the security-clearance exclusion",
                deleted_clearance_jobs,
            )
        ineligible_hashes = []
        for row in database.list_jobs(0):
            existing_job = Job(
                title=row.get("title", ""),
                company=row.get("company", ""),
                location=row.get("location", ""),
                description=row.get("description", ""),
                employment_type=row.get("employment_type", ""),
            )
            if not is_eligible_job(existing_job):
                ineligible_hashes.append(row.get("job_hash", ""))
        deleted_ineligible_jobs = database.delete_jobs_by_hashes(ineligible_hashes)
        if deleted_ineligible_jobs:
            logger.info(
                "Deleted %d previously stored jobs that no longer match eligibility filters",
                deleted_ineligible_jobs,
            )
        output_path = export_excel(database, excel_path, sources, keywords, settings, logger)
        logger.info("Excel updated: %s", output_path)
        website_settings = settings.get("website", {})
        website_path = export_website(
            database,
            resolve_path(website_settings.get("output_dir", "docs")),
            int(website_settings.get("minimum_export_score", 35)),
        )
        logger.info("Website data updated: %s", website_path)
        logger.info(
            "Run complete. Sources: %d, Jobs found: %d, New jobs: %d, Errors: %d, Duration: %.2fs",
            stats["sources_checked"], stats["jobs_found"], stats["new_jobs_added"],
            len(stats["errors"]), stats["duration_seconds"],
        )
        return 0 if not stats["errors"] else 1
    except Exception:
        logger.exception("Job Radar run failed")
        return 2
    finally:
        database.close()


if __name__ == "__main__":
    sys.exit(run())
