import os
import tempfile
import unittest
from unittest.mock import patch

import app as app_module
import db
from models import Job


def arbeitnow_job(**kw):
    j = Job(company="Acme", ats_type="arbeitnow", ats_job_id="1",
            title="Analytics Engineer", location_raw="Berlin",
            description="desc", apply_url="https://www.arbeitnow.com/jobs/companies/acme/analytics-1",
            posted_at="2026-09-01T00:00:00Z", is_startup=False)
    j.city = "berlin"; j.role_family = "data_eng"; j.sponsorship = "silent"
    j.match_score = 0.8; j.match_reasons = ["skills"]
    for k, v in kw.items():
        setattr(j, k, v)
    return j


class TestIsArbeitnowUrl(unittest.TestCase):
    def test_recognizes_any_arbeitnow_tld(self):
        self.assertTrue(app_module._is_arbeitnow_url("https://www.arbeitnow.com/jobs/x"))
        self.assertTrue(app_module._is_arbeitnow_url("https://arbeitnow.com/jobs/x"))
        self.assertTrue(app_module._is_arbeitnow_url("https://www.arbeitnow.fr/jobs/x"))
        self.assertTrue(app_module._is_arbeitnow_url("https://www.arbeitnow.co/jobs/x"))

    def test_rejects_other_hosts(self):
        self.assertFalse(app_module._is_arbeitnow_url("https://jobs.ashbyhq.com/acme/x"))
        self.assertFalse(app_module._is_arbeitnow_url("https://boards.greenhouse.io/acme/jobs/1"))
        self.assertFalse(app_module._is_arbeitnow_url(""))


class TestResolveArbeitnowApplyUrl(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.conn = db.connect(os.path.join(self.tmp, "t.db"))
        db.init_db(self.conn)

    def tearDown(self):
        self.conn.close()

    def _seeded(self, **kw):
        job = arbeitnow_job(**kw)
        db.upsert_jobs(self.conn, [job])
        return db.get_job(self.conn, job.id)

    def test_external_redirect_updates_and_persists(self):
        row = self._seeded()
        with patch("http_util.resolve_redirect", return_value=(302, "https://jobs.ashbyhq.com/acme/xyz/application")):
            app_module._resolve_arbeitnow_apply_url(self.conn, row)
        self.assertEqual(row["apply_url"], "https://jobs.ashbyhq.com/acme/xyz/application")
        self.assertEqual(db.get_job(self.conn, row["id"])["apply_url"],
                         "https://jobs.ashbyhq.com/acme/xyz/application")

    def test_200_means_the_apply_route_itself_is_final(self):
        row = self._seeded()
        with patch("http_util.resolve_redirect", return_value=(200, None)):
            app_module._resolve_arbeitnow_apply_url(self.conn, row)
        self.assertEqual(row["apply_url"], "https://www.arbeitnow.com/jobs/companies/acme/analytics-1/apply")

    def test_404_leaves_apply_url_unchanged(self):
        row = self._seeded()
        original = row["apply_url"]
        with patch("http_util.resolve_redirect", return_value=(404, None)):
            app_module._resolve_arbeitnow_apply_url(self.conn, row)
        self.assertEqual(row["apply_url"], original)

    def test_network_failure_leaves_apply_url_unchanged(self):
        row = self._seeded()
        original = row["apply_url"]
        with patch("http_util.resolve_redirect", return_value=None):
            app_module._resolve_arbeitnow_apply_url(self.conn, row)
        self.assertEqual(row["apply_url"], original)

    def test_redirect_back_to_own_domain_is_ignored(self):
        row = self._seeded()
        original = row["apply_url"]
        with patch("http_util.resolve_redirect",
                    return_value=(302, "https://www.arbeitnow.com/jobs/companies/acme/analytics-1")):
            app_module._resolve_arbeitnow_apply_url(self.conn, row)
        self.assertEqual(row["apply_url"], original)

    def test_non_arbeitnow_job_is_skipped_without_a_network_call(self):
        job = arbeitnow_job(ats_type="greenhouse", apply_url="https://boards.greenhouse.io/acme/jobs/1")
        db.upsert_jobs(self.conn, [job])
        row = db.get_job(self.conn, job.id)
        with patch("http_util.resolve_redirect") as m:
            app_module._resolve_arbeitnow_apply_url(self.conn, row)
        m.assert_not_called()

    def test_already_resolved_job_is_skipped_without_a_network_call(self):
        row = self._seeded(apply_url="https://jobs.ashbyhq.com/acme/xyz/application")
        with patch("http_util.resolve_redirect") as m:
            app_module._resolve_arbeitnow_apply_url(self.conn, row)
        m.assert_not_called()

    def test_localized_tld_is_recognized_and_resolved(self):
        # Arbeitnow runs the same platform on country TLDs (.fr, .co, ...) —
        # a job harvested from arbeitnow.fr must resolve the same way as .com.
        row = self._seeded(apply_url="https://www.arbeitnow.fr/jobs/companies/vibe/data-engineer-295755")
        with patch("http_util.resolve_redirect",
                    return_value=(302, "https://jobs.ashbyhq.com/vibe/45d3/application")) as m:
            app_module._resolve_arbeitnow_apply_url(self.conn, row)
        m.assert_called_once_with("https://www.arbeitnow.fr/jobs/companies/vibe/data-engineer-295755/apply")
        self.assertEqual(row["apply_url"], "https://jobs.ashbyhq.com/vibe/45d3/application")

    def test_redirect_back_to_own_localized_domain_is_ignored(self):
        row = self._seeded(apply_url="https://www.arbeitnow.fr/jobs/companies/vibe/data-engineer-295755")
        original = row["apply_url"]
        with patch("http_util.resolve_redirect",
                    return_value=(302, "https://www.arbeitnow.fr/jobs/companies/vibe/data-engineer-295755")):
            app_module._resolve_arbeitnow_apply_url(self.conn, row)
        self.assertEqual(row["apply_url"], original)


if __name__ == "__main__":
    unittest.main()
