import unittest

from ranker import score_job


class TestRanker(unittest.TestCase):
    def test_relevant_beats_irrelevant(self):
        strong, _ = score_job(
            "Penetration Tester",
            "Red team, Active Directory, Azure, BloodHound, Impacket, Burp Suite, privilege escalation.",
            "2026-09-05T00:00:00Z",
        )
        weak, _ = score_job("Office Manager", "Manage the office and supplies.", "2026-09-05T00:00:00Z")
        self.assertGreater(strong, weak)
        self.assertGreater(strong, 0.5)

    def test_title_match_gives_reasons(self):
        score, reasons = score_job("Red Team Engineer", "Active Directory and Azure attack paths.",
                                   "2026-09-01T00:00:00Z")
        self.assertGreater(score, 0.0)
        self.assertTrue(any("skills" in r.lower() or "role" in r.lower() for r in reasons))

    def test_internship_boost_ranks_pfe_first(self):
        base, _ = score_job("Penetration Tester", "Active Directory, Azure, red team.",
                            "2026-09-05T00:00:00Z")
        intern, reasons = score_job("Penetration Testing Intern (PFE)",
                                    "Active Directory, Azure, red team.", "2026-09-05T00:00:00Z")
        self.assertGreater(intern, base)
        self.assertTrue(any("intern" in r.lower() or "pfe" in r.lower() for r in reasons))

    def test_score_bounded(self):
        score, _ = score_job("AI Engineer", "python " * 200, "2026-09-10T00:00:00Z")
        self.assertLessEqual(score, 1.0)
        self.assertGreaterEqual(score, 0.0)

    def test_recency_helps(self):
        recent, _ = score_job("Backend Engineer", "Python backend.", "2026-09-10T00:00:00Z")
        old, _ = score_job("Backend Engineer", "Python backend.", "2026-01-01T00:00:00Z")
        self.assertGreater(recent, old)


if __name__ == "__main__":
    unittest.main()
