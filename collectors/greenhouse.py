from __future__ import annotations

from collectors.base import BaseCollector, CollectorError, Job
from utils.text import html_to_text


class GreenhouseCollector(BaseCollector):
    is_api = True

    def fetch_jobs(self) -> list[Job]:
        token = self.source_config.get("board_token")
        if not token:
            raise CollectorError("Greenhouse source requires board_token")
        url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
        payload = self.get(url, params={"content": "true"}).json()
        postings = payload.get("jobs", [])
        if not isinstance(postings, list):
            raise CollectorError("Unexpected Greenhouse API response")

        company = self.source_config.get("company", self.source_config.get("name", ""))
        jobs = []
        for item in postings:
            location = item.get("location") or {}
            offices = item.get("offices") or []
            location_name = location.get("name", "") if isinstance(location, dict) else location
            if not location_name and offices:
                location_name = ", ".join(
                    office.get("name", "") for office in offices if office.get("name")
                )
            jobs.append(
                Job(
                    title=item.get("title", "").strip(),
                    company=company,
                    location=location_name,
                    url=item.get("absolute_url", ""),
                    source_name=self.source_config.get("name", ""),
                    source_type="greenhouse",
                    description=html_to_text(item.get("content")),
                    employment_type="",
                    date_posted=item.get("updated_at", ""),
                    raw_data=item,
                )
            )
        return [job for job in jobs if job.title]

