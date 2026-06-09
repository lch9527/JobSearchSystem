import json
import tempfile
import unittest
from pathlib import Path

from collectors.base import Job
from storage.db import Database
from storage.web_writer import export_website
from utils.hashing import create_job_hash


class WebWriterTests(unittest.TestCase):
    def test_exports_public_fields_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            database = Database(root / "jobs.sqlite")
            job = Job(
                title="Rendering Engineer",
                company="Acme",
                location="Remote",
                url="https://example.com/jobs/1",
                source_name="Test",
                source_type="lever",
                description="Private long description",
                raw_data={"internal": "payload"},
                match_score=80,
                match_reason="Matched rendering",
            )
            job.job_hash = create_job_hash(job.title, job.company, job.url, job.location)
            database.upsert_job(job, "2026-06-08T09:00:00-04:00")
            database.update_manual_fields(job.job_hash, None, "Interested", "Private note")

            output = export_website(database, root / "docs", 35)
            payload = json.loads(output.read_text(encoding="utf-8"))
            exported = payload["jobs"][0]

            self.assertEqual(exported["title"], "Rendering Engineer")
            self.assertEqual(exported["status"], "Interested")
            self.assertNotIn("notes", exported)
            self.assertIn("job_hash", exported)
            self.assertNotIn("description", exported)
            self.assertNotIn("raw_data", exported)
            database.close()
