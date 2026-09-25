import unittest

import harvester
import prefs as prefs_mod
from models import Job

SECURITY = {"locations": [], "role_families": ["offensive_security", "appsec", "cloud_grc",
                                               "security_other", "blue_team"]}


def job(title, desc=""):
    return harvester.enrich(Job(company="GitLab", ats_type="greenhouse", ats_job_id=title,
                                title=title, location_raw="Remote", description=desc))


class TestTitleRelevance(unittest.TestCase):
    def test_security_words_in_description_are_not_enough(self):
        j = job("Backend Engineer, Verify", "Ship SAST and DAST scanners in our DevSecOps platform.")
        self.assertFalse(harvester.keep(j, SECURITY))

    def test_non_technical_security_titles_dropped(self):
        self.assertFalse(harvester.keep(job("Cybersecurity Account Executive"), SECURITY))
        self.assertFalse(harvester.keep(job("Security Sales Engineer"), SECURITY))

    def test_pentest_roles_kept(self):
        self.assertTrue(harvester.keep(job("Penetration Testing Intern"), SECURITY))
        self.assertTrue(harvester.keep(job("Stage PFE - Pentest"), SECURITY))
        self.assertTrue(harvester.keep(job("Junior Red Team Operator"), SECURITY))


if __name__ == "__main__":
    unittest.main()
