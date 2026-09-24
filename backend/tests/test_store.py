import os
import tempfile
import unittest

import db
import queue_io
from models import Job


def sample_job(**kw):
    j = Job(company="Acme", ats_type="greenhouse", ats_job_id="1",
            title="ML Engineer", location_raw="Paris, France",
            description="Python Spark", apply_url="https://x/1",
            posted_at="2026-09-01T00:00:00Z", is_startup=True)
    j.city = "paris"; j.role_family = "ai_ml"; j.sponsorship = "silent"
    j.match_score = 0.8; j.match_reasons = ["skills"]
    for k, v in kw.items():
        setattr(j, k, v)
    return j


class TestDB(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.conn = db.connect(os.path.join(self.tmp, "t.db"))
        db.init_db(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_upsert_and_get(self):
        job = sample_job()
        db.upsert_jobs(self.conn, [job])
        rows = db.get_jobs(self.conn)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "ML Engineer")
        self.assertEqual(rows[0]["match_reasons"], ["skills"])
        self.assertTrue(rows[0]["is_startup"])

    def test_status_transition_survives_reharvest(self):
        job = sample_job()
        db.upsert_jobs(self.conn, [job])
        db.set_status(self.conn, job.id, "applied")
        db.upsert_jobs(self.conn, [sample_job()])  # re-harvest same job
        self.assertEqual(db.get_job(self.conn, job.id)["status"], "applied")

    def test_mark_closed(self):
        job = sample_job()
        db.upsert_jobs(self.conn, [job])
        db.mark_closed(self.conn, "Acme", active_ids=[])  # job vanished
        self.assertEqual(db.get_job(self.conn, job.id)["status"], "closed")

    def test_engaged_not_closed(self):
        job = sample_job()
        db.upsert_jobs(self.conn, [job])
        db.set_status(self.conn, job.id, "applied")
        db.mark_closed(self.conn, "Acme", active_ids=[])
        self.assertEqual(db.get_job(self.conn, job.id)["status"], "applied")

    def test_filters(self):
        db.upsert_jobs(self.conn, [sample_job(), sample_job(ats_job_id="2", city="london", role_family="swe")])
        self.assertEqual(len(db.get_jobs(self.conn, city="paris")), 1)
        self.assertEqual(len(db.get_jobs(self.conn, role_family="swe")), 1)
        self.assertEqual(len(db.get_jobs(self.conn)), 2)

    def test_applied_events_keeps_first_timestamp_per_job(self):
        job = sample_job()
        db.upsert_jobs(self.conn, [job])
        db.log_event(self.conn, job.id, "status:applied", {})
        # a later status change on the same job (e.g. interview) must not
        # displace the original "marked applied" timestamp
        db.log_event(self.conn, job.id, "status:interview", {})
        events = db.applied_events(self.conn)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["job_id"], job.id)

    def test_applied_events_ignores_other_actions(self):
        job = sample_job()
        db.upsert_jobs(self.conn, [job])
        db.log_event(self.conn, job.id, "dismiss", {})
        db.log_event(self.conn, job.id, "queue", {})
        self.assertEqual(db.applied_events(self.conn), [])


class TestQueue(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        queue_io.PENDING_DIR = os.path.join(self.tmp, "pending")
        queue_io.APPLICATIONS_DIR = os.path.join(self.tmp, "applications")
        queue_io.CV_PATH = os.path.join(self.tmp, "cv.md")
        queue_io.PREFS_PATH = os.path.join(self.tmp, "preferences.md")
        with open(queue_io.CV_PATH, "w", encoding="utf-8") as f:
            f.write("# Sami\nPython, Spark")
        with open(queue_io.PREFS_PATH, "w", encoding="utf-8") as f:
            f.write("voice rules")

    def test_write_pending_payload(self):
        import json
        path = queue_io.write_pending(sample_job().to_row())
        self.assertTrue(os.path.isfile(path))
        d = json.load(open(path, encoding="utf-8"))
        self.assertEqual(d["company_slug"], "acme")
        self.assertIn("preferences_markdown", d)

    def test_done_ids_and_read(self):
        cdir = os.path.join(queue_io.APPLICATIONS_DIR, "acme")
        os.makedirs(cdir, exist_ok=True)
        with open(os.path.join(cdir, "xyz.md"), "w", encoding="utf-8") as f:
            f.write("# note")
        with open(os.path.join(cdir, "cover-letter.md"), "w", encoding="utf-8") as f:
            f.write("Dear team")
        self.assertEqual(queue_io.done_ids(), {"xyz"})       # cover-letter excluded
        mats = queue_io.read_materials("xyz")
        self.assertIn("# note", mats)
        self.assertIn("Dear team", mats)                     # company letter appended
        self.assertIsNone(queue_io.read_materials("nope"))


if __name__ == "__main__":
    unittest.main()
