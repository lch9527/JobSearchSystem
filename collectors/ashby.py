from __future__ import annotations

from collectors.base import BaseCollector, CollectorError, Job
from utils.text import html_to_text


class AshbyCollector(BaseCollector):
    is_api = True

    def fetch_jobs(self) -> list[Job]:
        token = self.source_config.get("board_token")
        if not token:
            raise CollectorError("Ashby source requires board_token")
        url = f"https://api.ashbyhq.com/posting-api/job-board/{token}"
        payload = self.get(url).json()
        postings = payload.get("jobs", [])
        if not isinstance(postings, list):
            raise CollectorError("Unexpected Ashby API response")

        company = self.source_config.get("company", self.source_config.get("name", ""))
        jobs = []
        for item in postings:
            location = item.get("location", "")
            if isinstance(location, dict):
                location = location.get("name", "")
            jobs.append(
                Job(
                    title=item.get("title", "").strip(),
                    company=company,
                    location=location,
                    url=item.get("jobUrl") or item.get("applyUrl", ""),
                    source_name=self.source_config.get("name", ""),
                    source_type="ashby",
                    description=html_to_text(
                        item.get("descriptionHtml") or item.get("description")
                    ),
                    salary=item.get("compensation", ""),
                    employment_type=item.get("employmentType", ""),
                    date_posted=item.get("publishedAt", ""),
                    raw_data=item,
                )
            )
        return [job for job in jobs if job.title]

