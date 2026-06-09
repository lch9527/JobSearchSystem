from __future__ import annotations

import re

from collectors.base import Job
from utils.text import normalize_text


EXPORT_CONTROL_PHRASE = normalize_text(
    "Must be a U.S. Person due to required access to U.S. export controlled information or facilities"
)


def _contains(text: str, keyword: str) -> bool:
    normalized_keyword = normalize_text(keyword)
    if not normalized_keyword:
        return False
    pattern = rf"(?<!\w){re.escape(normalized_keyword)}(?!\w)"
    return re.search(pattern, text) is not None


def score_job(job: Job, keyword_config: dict) -> tuple[int, str]:
    title = normalize_text(job.title)
    description = normalize_text(job.description)
    combined = f"{title} {description}"
    additions: list[str] = []
    penalties: list[str] = []
    score = 0.0

    for entry in keyword_config.get("title_boost_keywords", []):
        keyword = str(entry.get("keyword", ""))
        weight = float(entry.get("weight", 0))
        if _contains(title, keyword):
            score += weight
            additions.append(f'title "{keyword}" +{weight:g}')

    for entry in keyword_config.get("include_keywords", []):
        keyword = str(entry.get("keyword", ""))
        weight = float(entry.get("weight", 0))
        if _contains(title, keyword):
            title_weight = weight * 1.5
            score += title_weight
            additions.append(f'title "{keyword}" +{title_weight:g}')
        elif _contains(description, keyword):
            score += weight
            additions.append(f'"{keyword}" +{weight:g}')

    for entry in keyword_config.get("exclude_keywords", []):
        keyword = str(entry.get("keyword", ""))
        penalty = float(entry.get("penalty", 0))
        if _contains(combined, keyword):
            score -= penalty
            penalties.append(f'"{keyword}" -{penalty:g}')

    if EXPORT_CONTROL_PHRASE and EXPORT_CONTROL_PHRASE in combined:
        score -= 1000
        penalties.append(
            '"Must be a U.S. Person due to required access to U.S. export controlled information or facilities" -1000'
        )

    final_score = max(0, min(100, round(score)))
    if additions:
        reason = "Matched: " + ", ".join(additions)
    else:
        reason = "No configured positive keywords matched"
    if penalties:
        reason += ". Penalties: " + ", ".join(penalties)
    return final_score, reason

