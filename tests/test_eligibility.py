import unittest

from collectors.base import Job
from matching.eligibility import (
    is_eligible_job,
    is_internship,
    is_us_location,
    requires_disallowed_security_clearance,
)


class EligibilityTests(unittest.TestCase):
    def test_accepts_us_locations(self):
        self.assertTrue(is_us_location("Remote - United States"))
        self.assertTrue(is_us_location("San Francisco, CA"))
        self.assertTrue(is_us_location("Austin, Texas"))
        self.assertTrue(is_us_location("Austin"))
        self.assertTrue(is_us_location("Pittsburgh"))

    def test_rejects_unknown_or_non_us_locations(self):
        self.assertFalse(is_us_location("Remote"))
        self.assertFalse(is_us_location("Paris, France"))
        self.assertFalse(is_us_location(""))

    def test_rejects_internships(self):
        self.assertTrue(is_internship(Job(title="Rendering Engineer Intern")))
        self.assertTrue(is_internship(Job(title="Graphics Engineer", employment_type="Co-op")))
        self.assertFalse(is_internship(Job(title="Rendering Engineer", description="Mentor interns.")))
        self.assertFalse(is_internship(Job(title="Rendering Engineer")))

    def test_eligible_job_requires_us_and_not_internship(self):
        self.assertTrue(is_eligible_job(Job(title="Rendering Engineer", location="Seattle, WA")))
        self.assertFalse(is_eligible_job(Job(title="Rendering Engineer Intern", location="Seattle, WA")))
        self.assertFalse(is_eligible_job(Job(title="Rendering Engineer", location="Remote")))

    def test_rejects_secret_security_clearance_requirement(self):
        job = Job(
            title="Rendering Engineer",
            location="Seattle, WA",
            description="Eligible to obtain and maintain an active U.S. Secret security clearance.",
        )
        self.assertTrue(requires_disallowed_security_clearance(job))
        self.assertFalse(is_eligible_job(job))

    def test_rejects_related_clearance_language(self):
        blocked_descriptions = [
            "This role requires an active Secret clearance.",
            "Candidates must be eligible to obtain and maintain a U.S. security clearance.",
            "Clearance Required.",
            "Current Top Secret security clearance preferred.",
            "Active clearance required for program access.",
            "DoD clearance is required.",
        ]
        for description in blocked_descriptions:
            with self.subTest(description=description):
                job = Job(
                    title="Rendering Engineer",
                    company="Anduril Industries",
                    location="Seattle, WA",
                    description=description,
                )
                self.assertTrue(requires_disallowed_security_clearance(job))
                self.assertFalse(is_eligible_job(job))

    def test_company_is_not_blocked_without_clearance_language(self):
        self.assertTrue(
            is_eligible_job(
                Job(
                    title="Rendering Engineer",
                    company="Anduril Industries",
                    location="Seattle, WA",
                    description="Build simulation tools.",
                )
            )
        )
