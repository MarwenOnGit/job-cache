import json
import os
import unittest

from adapters import greenhouse, lever, ashby, workable
import harvester

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def load(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return json.load(f)


class TestGreenhouse(unittest.TestCase):
    def test_parse(self):
        company = {"name": "Acme", "ats_slug": "acme", "is_startup": True}
        jobs = greenhouse.parse(company, load("greenhouse.json"))
        self.assertEqual(len(jobs), 2)
        ml = jobs[0]
        self.assertEqual(ml.title, "Machine Learning Engineer")
        self.assertEqual(ml.location_raw, "Paris, France")
        self.assertIn("Build ML systems", ml.description)      # HTML entities decoded
        self.assertNotIn("<p>", ml.description)                # tags stripped
        self.assertEqual(ml.apply_url, "https://boards.greenhouse.io/acme/jobs/123")
        self.assertTrue(ml.is_startup)
        self.assertEqual(ml.ats_type, "greenhouse")


class TestLever(unittest.TestCase):
    def test_parse(self):
        company = {"name": "Acme", "ats_slug": "acme", "is_startup": True}
        jobs = lever.parse(company, load("lever.json"))
        self.assertEqual(len(jobs), 1)
        j = jobs[0]
        self.assertEqual(j.title, "Data Engineer")
        self.assertEqual(j.location_raw, "London, UK")
        self.assertIn("ETL pipelines", j.description)
        self.assertEqual(j.posted_at, "1756000000000")


class TestAshby(unittest.TestCase):
    def test_parse(self):
        company = {"name": "Acme", "ats_slug": "acme", "is_startup": False}
        jobs = ashby.parse(company, load("ashby.json"))
        self.assertEqual(len(jobs), 1)
        j = jobs[0]
        self.assertEqual(j.title, "Software Engineer, Backend")
        self.assertEqual(j.location_raw, "Brussels, Belgium")
        self.assertFalse(j.is_startup)


class TestWorkable(unittest.TestCase):
    def test_parse(self):
        company = {"name": "Hugging Face", "ats_slug": "huggingface", "is_startup": True}
        jobs = workable.parse(company, load("workable.json"))
        self.assertEqual(len(jobs), 1)
        j = jobs[0]
        self.assertEqual(j.ats_job_id, "F4C096B22E")
        self.assertIn("Paris", j.location_raw)
        self.assertIn("Remote", j.location_raw)          # telecommuting flag
        self.assertNotIn("<p>", j.description)
        self.assertEqual(j.apply_url, "https://apply.workable.com/j/F4C096B22E")
        self.assertEqual(j.posted_at, "2026-08-01")


class TestEnrichAndKeep(unittest.TestCase):
    def test_ml_job_enriched_and_kept(self):
        company = {"name": "Acme", "ats_slug": "acme", "is_startup": True}
        ml, office = greenhouse.parse(company, load("greenhouse.json"))
        harvester.enrich(ml)
        self.assertEqual(ml.city, "paris")
        self.assertIn(ml.role_family, ("ai_ml", "ai_agentic"))
        self.assertEqual(ml.sponsorship, "likely_sponsors")
        self.assertGreater(ml.match_score, 0.3)
        self.assertTrue(harvester.keep(ml))

    def test_non_tech_job_dropped(self):
        company = {"name": "Acme", "ats_slug": "acme", "is_startup": True}
        _, office = greenhouse.parse(company, load("greenhouse.json"))
        harvester.enrich(office)
        self.assertIsNone(office.role_family)     # "Office Manager" not a target family
        self.assertFalse(harvester.keep(office))

    def test_lever_no_sponsorship_flag(self):
        company = {"name": "Acme", "ats_slug": "acme", "is_startup": True}
        j = lever.parse(company, load("lever.json"))[0]
        harvester.enrich(j)
        self.assertEqual(j.city, "london")
        self.assertEqual(j.role_family, "data_eng")
        self.assertEqual(j.sponsorship, "no_sponsorship")
        self.assertTrue(harvester.keep(j))


if __name__ == "__main__":
    unittest.main()
