from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from collectors.base import BaseCollector, CollectorError, Job
from utils.text import clean_text


class HtmlPageCollector(BaseCollector):
    def fetch_jobs(self) -> list[Job]:
        source_url = self.source_config.get("url")
        if not source_url:
            raise CollectorError("HTML source requires url")

        response = self.get(source_url)
        soup = BeautifulSoup(response.text, "html.parser")
        selector = self.source_config.get("job_link_selector", "a")
        title_selector = self.source_config.get("title_selector")
        location_selector = self.source_config.get("location_selector")
        description_selector = self.source_config.get("description_selector")
        company = self.source_config.get("company", self.source_config.get("name", ""))

        jobs = []
        seen_urls = set()
        for element in soup.select(selector):
            link = element if element.name == "a" else element.select_one("a[href]")
            if not link or not link.get("href"):
                continue
            url = urljoin(source_url, link["href"])
            if url in seen_urls:
                continue
            container = element
            title_node = container.select_one(title_selector) if title_selector else None
            location_node = (
                container.select_one(location_selector) if location_selector else None
            )
            description_node = (
                container.select_one(description_selector)
                if description_selector
                else None
            )
            title = clean_text(
                (title_node.get_text(" ") if title_node else link.get_text(" "))
                or link.get("title")
                or link.get("aria-label")
            )
            if not title:
                continue
            seen_urls.add(url)
            jobs.append(
                Job(
                    title=title,
                    company=company,
                    location=clean_text(
                        location_node.get_text(" ") if location_node else ""
                    ),
                    url=url,
                    source_name=self.source_config.get("name", ""),
                    source_type="html",
                    description=clean_text(
                        description_node.get_text(" ") if description_node else ""
                    ),
                    raw_data={"source_page": source_url},
                )
            )
        return jobs

