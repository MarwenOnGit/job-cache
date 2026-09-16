import json
import os
import unittest

from adapters import arbeitnow, himalayas, jobicy, remoteok, remotive, themuse
import harvester

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def load(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return json.load(f)


class TestRemotive(unittest.TestCase):
    def test_parse(self):
        jobs = remotive.parse({"name": "Remotive"}, load("remotive.json"))
        self.assertEqual(len(jobs), 1)
        j = jobs[0]
        self.assertEqual(j.company, "Acme Remote")          # employer, not source
        self.assertEqual(j.ats_type, "remotive")
        self.assertEqual(j.title, "Backend Engineer")
        self.assertNotIn("<p>", j.description)
        harvester.enrich(j)
        self.assertEqual(j.city, "remote-eu")               # "Europe" -> remote-eu
        self.assertEqual(j.role_family, "swe")
        self.assertTrue(harvester.keep(j))


class TestArbeitnow(unittest.TestCase):
    def test_parse(self):
        jobs = arbeitnow.parse({"name": "Arbeitnow"}, load("arbeitnow.json"))
        self.assertEqual(len(jobs), 1)
        j = jobs[0]
        self.assertEqual(j.company, "Berlin Co")
        self.assertIn("Berlin", j.location_raw)
        self.assertIn("Remote", j.location_raw)             # remote flag appended
        harvester.enrich(j)
        self.assertEqual(j.city, "berlin")                  # specific city wins over remote
        self.assertEqual(j.role_family, "data_eng")
        self.assertTrue(harvester.keep(j))


class TestJobicy(unittest.TestCase):
    def test_parse(self):
        jobs = jobicy.parse({"name": "Jobicy"}, load("jobicy.json"))
        j = jobs[0]
        self.assertEqual(j.company, "Jobicy Co")
        harvester.enrich(j)
        self.assertEqual(j.city, "remote-eu")
        self.assertIn(j.role_family, ("ai_ml", "ai_agentic"))
        self.assertTrue(harvester.keep(j))


class TestHimalayas(unittest.TestCase):
    def test_parse(self):
        jobs = himalayas.parse({"name": "Himalayas"}, load("himalayas.json"))
        j = jobs[0]
        self.assertEqual(j.company, "Hima Co")
        self.assertEqual(j.apply_url, "https://himalayas.app/jobs/x")
        harvester.enrich(j)
        self.assertEqual(j.city, "remote-eu")
        self.assertEqual(j.role_family, "swe")


class TestRemoteOK(unittest.TestCase):
    def test_parse_skips_legal_notice(self):
        jobs = remoteok.parse({"name": "RemoteOK"}, load("remoteok.json"))
        self.assertEqual(len(jobs), 1)                      # legal notice row skipped
        j = jobs[0]
        self.assertEqual(j.company, "RO Co")
        self.assertEqual(j.title, "Backend Developer")
        harvester.enrich(j)
        self.assertEqual(j.city, "remote-global")           # "Worldwide" -> remote-global
        self.assertTrue(harvester.keep(j))


class TestTheMuse(unittest.TestCase):
    def test_parse(self):
        jobs = themuse.parse({"name": "The Muse"}, load("themuse.json"))
        j = jobs[0]
        self.assertEqual(j.company, "Muse Co")
        self.assertEqual(j.apply_url, "https://themuse.com/jobs/x")
        harvester.enrich(j)
        self.assertEqual(j.city, "london")
        self.assertEqual(j.role_family, "swe")
        self.assertTrue(harvester.keep(j))


if __name__ == "__main__":
    unittest.main()
