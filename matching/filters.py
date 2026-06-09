from __future__ import annotations

from collections.abc import Iterable

from collectors.base import Job


def exportable_jobs(jobs: Iterable[Job], minimum_score: int) -> list[Job]:
    return [job for job in jobs if job.match_score >= minimum_score]

