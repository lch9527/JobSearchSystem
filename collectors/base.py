from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import requests


@dataclass(slots=True)
class Job:
    title: str
    company: str = ""
    location: str = ""
    url: str = ""
    source_name: str = ""
    source_type: str = ""
    description: str = ""
    salary: str = ""
    employment_type: str = ""
    date_posted: str = ""
    raw_data: dict[str, Any] = field(default_factory=dict)
    job_hash: str = ""
    match_score: int = 0
    match_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CollectorError(RuntimeError):
    pass


class BaseCollector:
    is_api = False

    def __init__(self, source_config, rate_limiter, request_settings):
        self.source_config = source_config
        self.rate_limiter = rate_limiter
        self.timeout = int(request_settings.get("timeout_seconds", 20))
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": request_settings.get(
                    "user_agent", "LocalJobRadar/1.0 personal job search bot"
                ),
                "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
            }
        )

    def fetch_jobs(self) -> list[Job]:
        raise NotImplementedError

    def get(self, url: str, **kwargs) -> requests.Response:
        self.rate_limiter.wait(url, api=self.is_api)
        response = self.session.get(url, timeout=self.timeout, **kwargs)
        self.rate_limiter.record_response(url, response.status_code)
        if response.status_code == 403:
            raise CollectorError(f"HTTP 403 from {url}; source skipped")
        if response.status_code == 429:
            raise CollectorError(f"HTTP 429 from {url}; source backed off")
        response.raise_for_status()
        return response

