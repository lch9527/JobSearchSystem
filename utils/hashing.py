from __future__ import annotations

import hashlib

from utils.text import normalize_text, normalize_url


def create_job_hash(
    title: str,
    company: str | None,
    url: str | None,
    location: str | None = None,
) -> str:
    normalized_url = normalize_url(url)
    identity = (
        f"{normalize_text(title)}|{normalize_text(company)}|{normalized_url}"
        if normalized_url
        else (
            f"{normalize_text(title)}|{normalize_text(company)}|"
            f"{normalize_text(location)}"
        )
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()

