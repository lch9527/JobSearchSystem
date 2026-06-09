from __future__ import annotations

from collectors.base import BaseCollector, CollectorError, Job
from utils.text import html_to_text


class LeverCollector(BaseCollector):
    is_api = True

    def fetch_jobs(self) -> list[Job]:
        slug = self.source_config.get("company_slug")
        if not slug:
            raise CollectorError("Lever source requires company_slug")
        url = f"https://api.lever.co/v0/postings/{slug}"
        payload = self.get(url, params={"mode": "json"}).json()
        if not isinstance(payload, list):
            raise CollectorError("Unexpected Lever API response")

        company = self.source_config.get("company", self.source_config.get("name", ""))
        jobs = []
        for item in payload:
            categories = item.get("categories") or {}
            salary = item.get("salaryRange") or {}
            salary_text = ""
            if salary:
                salary_text = " - ".join(
                    str(value)
                    for value in (salary.get("min"), salary.get("max"))
                    if value is not None
                )
                if salary.get("currency"):
                    salary_text = f"{salary_text} {salary['currency']}".strip()
            description_parts = [
                item.get("descriptionPlain") or html_to_text(item.get("description")),
                html_to_text(item.get("additionalPlain") or item.get("additional")),
            ]
            jobs.append(
                Job(
                    title=item.get("text", "").strip(),
                    company=company,
                    location=categories.get("location", ""),
                    url=item.get("hostedUrl") or item.get("applyUrl", ""),
                    source_name=self.source_config.get("name", ""),
                    source_type="lever",
                    description=" ".join(part for part in description_parts if part),
                    salary=salary_text,
                    employment_type=categories.get("commitment", ""),
                    date_posted=str(item.get("createdAt") or ""),
                    raw_data=item,
                )
            )
        return [job for job in jobs if job.title]

