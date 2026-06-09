from __future__ import annotations

import random
import time
from collections import defaultdict
from urllib.parse import urlsplit


class RateLimitExceeded(RuntimeError):
    pass


class RateLimiter:
    def __init__(self, request_settings: dict, rate_settings: dict):
        self.max_total = int(request_settings.get("max_total_requests_per_run", 300))
        self.max_per_domain = int(
            rate_settings.get("max_requests_per_domain_per_run", 10)
        )
        self.max_per_api_source = int(
            rate_settings.get("max_requests_per_api_source_per_run", 50)
        )
        self.default_delay = (
            float(rate_settings.get("default_delay_min_seconds", 20)),
            float(rate_settings.get("default_delay_max_seconds", 60)),
        )
        self.api_delay = (
            float(rate_settings.get("api_delay_min_seconds", 3)),
            float(rate_settings.get("api_delay_max_seconds", 10)),
        )
        self.backoffs = list(rate_settings.get("backoff_seconds", [60, 120, 300, 600]))
        self.total_requests = 0
        self.domain_requests: dict[str, int] = defaultdict(int)
        self.last_request: dict[str, float] = {}
        self.backoff_attempts: dict[str, int] = defaultdict(int)

    def wait(self, url: str, api: bool = False) -> None:
        domain = urlsplit(url).netloc.casefold()
        domain_limit = self.max_per_api_source if api else self.max_per_domain
        if self.total_requests >= self.max_total:
            raise RateLimitExceeded("Maximum total requests reached for this run")
        if self.domain_requests[domain] >= domain_limit:
            raise RateLimitExceeded(f"Request limit reached for {domain}")

        minimum, maximum = self.api_delay if api else self.default_delay
        if domain in self.last_request:
            target_delay = random.uniform(minimum, maximum)
            elapsed = time.monotonic() - self.last_request[domain]
            if elapsed < target_delay:
                time.sleep(target_delay - elapsed)

        self.total_requests += 1
        self.domain_requests[domain] += 1
        self.last_request[domain] = time.monotonic()

    def record_response(self, url: str, status_code: int) -> None:
        if status_code != 429:
            return
        domain = urlsplit(url).netloc.casefold()
        attempt = self.backoff_attempts[domain]
        delay = self.backoffs[min(attempt, len(self.backoffs) - 1)]
        self.backoff_attempts[domain] += 1
        time.sleep(float(delay))

