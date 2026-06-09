from __future__ import annotations

import html
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup


TRACKING_PARAMETERS = {
    "gh_src",
    "lever-source",
    "source",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}


def normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).casefold()


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def html_to_text(value: str | None) -> str:
    if not value:
        return ""
    return clean_text(BeautifulSoup(html.unescape(value), "html.parser").get_text(" "))


def normalize_url(url: str | None) -> str:
    if not url:
        return ""
    parts = urlsplit(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.casefold() not in TRACKING_PARAMETERS
        and not key.casefold().startswith("utm_")
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(
        (
            parts.scheme.casefold(),
            parts.netloc.casefold(),
            path,
            urlencode(query, doseq=True),
            "",
        )
    )

