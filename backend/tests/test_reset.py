import os
import tempfile
import unittest

import harvester
import reset
from models import Job


class TestReset(unittest.TestCase):
    def test_wipe_removes_search_data_only(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ("jobs.db", "jobs.db-wal", "model.json", "preferences.json", "config.json"):
                open(os.path.join(d, name), "w").close()
            removed = reset.wipe(d)
            self.assertIn("jobs.db", removed)
            self.assertIn("model.json", removed)
            self.assertFalse(os.path.exists(os.path.join(d, "jobs.db")))
            self.assertTrue(os.path.exists(os.path.join(d, "config.json")))   # theme etc. kept

    def test_once_runs_a_single_time(self):
        with tempfile.TemporaryDirectory() as d:
            orig = (reset.DATA, reset.MARKER)
            reset.DATA, reset.MARKER = d, os.path.join(d, ".reset-x")
            try:
                db = os.path.join(d, "jobs.db")
                open(db, "w").close()
                reset.main(["--once"])                       # first launch: wipes
                self.assertFalse(os.path.exists(db))
                open(db, "w").close()
                reset.main(["--once"])                       # later launches: no-op
                self.assertTrue(os.path.exists(db))
            finally:
                reset.DATA, reset.MARKER = orig


class TestFitsLevel(unittest.TestCase):
    def _job(self, title, desc=""):
        j = Job(company="Acme", ats_type="lever", ats_job_id=title, title=title,
                location_raw="Paris, France", description=desc)
        return harvester.enrich(j)

    def test_intern_and_junior_kept(self):
        self.assertTrue(harvester.fits_level(self._job("Penetration Testing Intern")))
        self.assertTrue(harvester.fits_level(self._job("Junior Security Engineer")))

    def test_senior_and_many_years_dropped(self):
        self.assertFalse(harvester.fits_level(self._job("Senior Red Team Operator")))
        self.assertFalse(harvester.fits_level(
            self._job("Security Engineer", "You have 5+ years of experience in pentesting.")))


if __name__ == "__main__":
    unittest.main()
