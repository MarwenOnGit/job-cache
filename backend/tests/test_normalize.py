import unittest

from normalize import classify_city, classify_role_family, strip_html


class TestCity(unittest.TestCase):
    def test_cities(self):
        self.assertEqual(classify_city("Paris, France"), "paris")
        self.assertEqual(classify_city("Île-de-France"), "paris")
        self.assertEqual(classify_city("London, United Kingdom"), "london")
        self.assertEqual(classify_city("Brussels, Belgium"), "brussels")
        self.assertEqual(classify_city("Geneva, Switzerland"), "geneva")
        self.assertEqual(classify_city("Zurich"), "geneva")
        self.assertEqual(classify_city("Remote - Europe"), "remote-eu")
        self.assertEqual(classify_city("Remote"), "remote-eu")
        self.assertEqual(classify_city("New York, USA"), "other")
        self.assertEqual(classify_city(""), "other")


class TestRoleFamily(unittest.TestCase):
    def test_families(self):
        self.assertEqual(classify_role_family("Software Engineer, Backend"), "swe")
        self.assertEqual(classify_role_family("Data Engineer"), "data_eng")
        self.assertEqual(classify_role_family("Machine Learning Engineer"), "ai_ml")
        self.assertEqual(classify_role_family("LLM / Agentic Systems Engineer"), "ai_agentic")
        self.assertIsNone(classify_role_family("Office Manager"))
        self.assertIsNone(classify_role_family("Account Executive"))


class TestStripHtml(unittest.TestCase):
    def test_strip(self):
        self.assertEqual(strip_html("<p>Hello&amp;<br/>world</p>"), "Hello& world")
        self.assertEqual(strip_html(""), "")
        self.assertEqual(strip_html(None), "")


if __name__ == "__main__":
    unittest.main()
