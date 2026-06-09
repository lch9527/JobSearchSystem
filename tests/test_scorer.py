import unittest

from collectors.base import Job
from matching.scorer import score_job


class ScorerTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "include_keywords": [
                {"keyword": "C++", "weight": 10},
                {"keyword": "Vulkan", "weight": 15},
            ],
            "title_boost_keywords": [
                {"keyword": "Rendering Engineer", "weight": 30}
            ],
            "exclude_keywords": [{"keyword": "Sales", "penalty": 50}],
        }

    def test_relevant_job_scores_highly(self):
        job = Job(
            title="Rendering Engineer",
            description="Build Vulkan systems using C++.",
        )
        score, reason = score_job(job, self.config)
        self.assertEqual(score, 55)
        self.assertIn("Rendering Engineer", reason)
        self.assertIn("Vulkan", reason)

    def test_exclusion_penalty_clamps_at_zero(self):
        score, _ = score_job(Job(title="Sales Manager"), self.config)
        self.assertEqual(score, 0)
