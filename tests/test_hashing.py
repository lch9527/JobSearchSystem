import unittest

from utils.hashing import create_job_hash
from utils.text import normalize_url


class HashingTests(unittest.TestCase):
    def test_tracking_parameters_do_not_change_identity(self):
        clean = "https://example.com/jobs/123"
        tracked = clean + "?utm_source=test&gh_src=abc"
        self.assertEqual(normalize_url(tracked), clean)
        self.assertEqual(
            create_job_hash("Rendering Engineer", "Acme", clean),
            create_job_hash(" Rendering  Engineer ", "ACME", tracked),
        )

    def test_location_is_fallback_without_url(self):
        first = create_job_hash("Engineer", "Acme", "", "Boston")
        second = create_job_hash("Engineer", "Acme", "", "Seattle")
        self.assertNotEqual(first, second)
