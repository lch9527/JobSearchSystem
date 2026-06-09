import unittest

from utils.rate_limiter import RateLimitExceeded, RateLimiter


class RateLimiterTests(unittest.TestCase):
    def test_enforces_per_domain_limit(self):
        limiter = RateLimiter(
            {"max_total_requests_per_run": 10},
            {
                "default_delay_min_seconds": 0,
                "default_delay_max_seconds": 0,
                "max_requests_per_domain_per_run": 1,
            },
        )
        limiter.wait("https://example.com/one")
        with self.assertRaises(RateLimitExceeded):
            limiter.wait("https://example.com/two")
