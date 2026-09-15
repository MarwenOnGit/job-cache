import unittest

from seniority import classify_seniority, extract_required_years


class TestSeniority(unittest.TestCase):
    def test_junior(self):
        self.assertEqual(classify_seniority("Junior Software Engineer"), "junior")
        self.assertEqual(classify_seniority("Software Engineering Intern"), "junior")
        self.assertEqual(classify_seniority("Graduate Data Engineer"), "junior")

    def test_senior(self):
        self.assertEqual(classify_seniority("Senior Backend Engineer"), "senior_plus")
        self.assertEqual(classify_seniority("Staff ML Engineer"), "senior_plus")
        self.assertEqual(classify_seniority("Principal Engineer"), "senior_plus")
        self.assertEqual(classify_seniority("Engineering Lead"), "senior_plus")

    def test_mid(self):
        self.assertEqual(classify_seniority("Software Engineer"), "mid")
        self.assertEqual(classify_seniority("Backend Engineer, Payments"), "mid")

    def test_many_years_in_desc_implies_senior(self):
        self.assertEqual(classify_seniority("Software Engineer", "8+ years of experience required"),
                         "senior_plus")

    def test_extract_years(self):
        self.assertEqual(extract_required_years("You have 5+ years of experience"), 5)
        self.assertEqual(extract_required_years("3-5 years in backend"), 3)
        self.assertEqual(extract_required_years("Minimum 4 ans d'expérience"), 4)
        self.assertIsNone(extract_required_years("No specific requirement"))
        self.assertIsNone(extract_required_years(""))


if __name__ == "__main__":
    unittest.main()
