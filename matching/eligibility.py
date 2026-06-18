from __future__ import annotations

import re

from collectors.base import Job
from utils.text import normalize_text


US_LOCATION_PATTERNS = (
    re.compile(r"\bunited states\b", re.IGNORECASE),
    re.compile(r"\busa\b", re.IGNORECASE),
    re.compile(r"\bu\.s\.\b", re.IGNORECASE),
    re.compile(r"\bus\b", re.IGNORECASE),
    re.compile(r"\bremote[-\s]*(?:us|u\.s\.|united states)\b", re.IGNORECASE),
    re.compile(
        r"\b(alabama|alaska|arizona|arkansas|california|colorado|connecticut|"
        r"delaware|florida|georgia|hawaii|idaho|illinois|indiana|iowa|kansas|"
        r"kentucky|louisiana|maine|maryland|massachusetts|michigan|minnesota|"
        r"mississippi|missouri|montana|nebraska|nevada|new hampshire|new jersey|"
        r"new mexico|new york|north carolina|north dakota|ohio|oklahoma|oregon|"
        r"pennsylvania|rhode island|south carolina|south dakota|tennessee|texas|"
        r"utah|vermont|virginia|washington|west virginia|wisconsin|wyoming)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(AK|AL|AR|AZ|CA|CO|CT|DC|DE|FL|GA|HI|IA|ID|IL|IN|KS|KY|LA|MA|"
        r"MD|ME|MI|MN|MO|MS|MT|NC|ND|NE|NH|NJ|NM|NV|NY|OH|OK|OR|PA|RI|SC|"
        r"SD|TN|TX|UT|VA|VT|WA|WI|WV|WY)\b"
    ),
    re.compile(
        r"\b(austin|boston|chicago|colorado springs|fort collins|houston|"
        r"indianapolis|irvine|lehi|los angeles|miami|nashville|new york|nyc|"
        r"pittsburgh|provo|san diego|san francisco|santa monica|seattle|"
        r"washington,?\s+dc)\b",
        re.IGNORECASE,
    ),
)

INTERNSHIP_PATTERNS = (
    re.compile(r"\bintern(?:ship)?\b", re.IGNORECASE),
    re.compile(r"\bco[-\s]?op\b", re.IGNORECASE),
)

SECURITY_CLEARANCE_PATTERNS = (
    re.compile(
        r"\beligible to obtain and maintain an active u\.?s\.? secret security clearance\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\beligible to obtain and maintain\b.{0,120}\b(?:secret|top secret|ts/sci|security)\b.{0,40}\bclearance\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:active|current|obtain|maintain)\b.{0,40}\b(?:u\.?s\.?\s*)?(?:secret|top secret|ts/sci)\b.{0,40}\b(?:security\s*)?clearance\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:secret|top secret|ts/sci)\b.{0,40}\b(?:security\s*)?clearance\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:security|dod)\s+clearance\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bclearance required\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bactive clearance\b",
        re.IGNORECASE,
    ),
)

CLEARANCE_EXCLUSION_PHRASE = (
    "Eligible to obtain and maintain an active U.S. Secret security clearance"
)


def is_us_location(location: str) -> bool:
    return any(pattern.search(location or "") for pattern in US_LOCATION_PATTERNS)


def is_internship(job: Job) -> bool:
    text = " ".join(
        [
            normalize_text(job.title),
            normalize_text(job.employment_type),
        ]
    )
    return any(pattern.search(text) for pattern in INTERNSHIP_PATTERNS)


def requires_disallowed_security_clearance(job: Job) -> bool:
    text = " ".join(
        [
            normalize_text(job.title),
            normalize_text(job.employment_type),
            normalize_text(job.description),
        ]
    )
    return any(pattern.search(text) for pattern in SECURITY_CLEARANCE_PATTERNS)


def is_eligible_job(job: Job) -> bool:
    return (
        is_us_location(job.location)
        and not is_internship(job)
        and not requires_disallowed_security_clearance(job)
    )
