import json
import os
import tempfile
import unittest
from unittest.mock import patch

import app as app_module
import db
import learn
from tests.test_store import sample_job


class TestJobsListPayload(unittest.TestCase):
    """/api/jobs ships a short blurb, not full descriptions; search goes through
    /api/jobs/match instead."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        path = os.path.join(self.tmp, "t.db")
        conn = db.connect(path)
        db.init_db(conn)
        long_desc = "We build   data\npipelines. " + "Kafka and Spark at scale. " * 200
        db.upsert_jobs(conn, [
            sample_job(ats_job_id="1", title="Data Engineer", company="Acme", description=long_desc,
                       match_score=0.9, match_reasons=["skills: kafka"]),
            sample_job(ats_job_id="2", title="ML Engineer", company="Globex",
                       description="PyTorch research on LLM agents", match_score=0.5),
            sample_job(ats_job_id="3", title="Backend Developer", company="Initech",
                       description="Go services", match_score=0.2),
        ])
        conn.commit()
        conn.close()
        real_connect = db.connect
        self.patches = [patch.object(db, "connect", lambda p=None: real_connect(path)),
                        patch.object(app_module, "_reconcile", lambda conn: None)]
        for p in self.patches:
            p.start()
        learn.invalidate()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        learn.invalidate()

    def _list(self, **kw):
        return json.loads(app_module.list_jobs(**{"level": "all", **kw}).body)

    def _match(self, *terms):
        return set(json.loads(app_module.match_jobs(list(terms)).body)["ids"])

    def test_list_has_blurb_not_description(self):
        data = self._list()
        self.assertEqual(data["count"], 3)
        for j in data["jobs"]:
            self.assertNotIn("description", j)
            self.assertLessEqual(len(j["blurb"]), app_module._BLURB_CHARS)
        de = next(j for j in data["jobs"] if j["title"] == "Data Engineer")
        self.assertTrue(de["blurb"].startswith("We build data pipelines. Kafka"))

    def test_limit_keeps_total_count_and_order(self):
        full = self._list(sort="for_you")
        top = self._list(sort="for_you", limit=2)
        self.assertEqual(top["count"], 3)
        self.assertEqual([j["id"] for j in top["jobs"]], [j["id"] for j in full["jobs"][:2]])

    def test_single_job_still_has_full_description(self):
        jid = self._list()["jobs"][0]["id"]
        with patch.object(app_module, "_resolve_arbeitnow_apply_url", lambda c, j: None):
            job = app_module.get_job(jid)
        self.assertGreater(len(job["description"]), 1000)

    def test_match_searches_title_company_description_and_reasons(self):
        ids = {j["title"]: j["id"] for j in self._list()["jobs"]}
        self.assertEqual(self._match("pytorch"), {ids["ML Engineer"]})         # description
        self.assertEqual(self._match("INITECH"), {ids["Backend Developer"]})   # company, any case
        self.assertEqual(self._match("skills: kafka"), {ids["Data Engineer"]})  # match reasons
        self.assertEqual(self._match("engineer"), {ids["Data Engineer"], ids["ML Engineer"]})

    def test_match_requires_every_term(self):
        ids = {j["title"]: j["id"] for j in self._list()["jobs"]}
        self.assertEqual(self._match("kafka", "spark"), {ids["Data Engineer"]})
        self.assertEqual(self._match("kafka", "pytorch"), set())

    def test_match_with_no_terms_returns_everything(self):
        self.assertEqual(len(self._match()), 3)
        self.assertEqual(len(self._match("  ")), 3)


class TestBlurb(unittest.TestCase):
    def test_collapses_whitespace_and_truncates(self):
        self.assertEqual(app_module._blurb("  a\t\n b  c  "), "a b c")
        self.assertEqual(app_module._blurb(None), "")
        self.assertEqual(len(app_module._blurb("word " * 500)), app_module._BLURB_CHARS)


class TestFeatureCache(unittest.TestCase):
    def setUp(self):
        learn._FEATURE_CACHE.clear()

    def test_reharvest_invalidates_cached_features(self):
        job = {"id": "j1", "last_seen": "t1", "title": "Python Engineer", "description": "kafka"}
        self.assertIn(("kw", "kafka"), learn.features(job))
        # same id + same last_seen: served from cache
        self.assertIs(learn.features(dict(job)), learn.features(job))
        # a harvest rewrites the row and bumps last_seen -> recomputed
        changed = {**job, "last_seen": "t2", "description": "rust"}
        feats = learn.features(changed)
        self.assertIn(("kw", "rust"), feats)
        self.assertNotIn(("kw", "kafka"), feats)

    def test_jobs_without_id_are_not_cached(self):
        learn.features({"title": "Data Engineer", "description": "sql"})
        self.assertEqual(learn._FEATURE_CACHE, {})

    def test_blended_score_accepts_precomputed_score(self):
        model = {"ready": True, "weights": {"kw:python": 1.0}}
        job = {"title": "Python Dev", "description": "", "match_score": 0.4}
        self.assertEqual(learn.blended_score(job, model),
                         learn.blended_score(job, model, learn.score(job, model)))


if __name__ == "__main__":
    unittest.main()
