import unittest

from normalize import classify_city, classify_role_family, extract_apply_link, strip_html


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
        # North America is now kept (the user is open to roles abroad), not dropped.
        self.assertEqual(classify_city("New York, USA"), "usa")
        self.assertEqual(classify_city("Toronto, Canada"), "canada")
        self.assertEqual(classify_city(""), "other")

    def test_broadened_eu_hubs(self):
        self.assertEqual(classify_city("Amsterdam, Netherlands"), "amsterdam")
        self.assertEqual(classify_city("Berlin, Germany"), "berlin")
        self.assertEqual(classify_city("Dublin, Ireland"), "dublin")
        self.assertEqual(classify_city("Barcelona, Spain"), "barcelona")
        self.assertEqual(classify_city("Lisbon, Portugal"), "lisbon")
        self.assertEqual(classify_city("Munich"), "munich")
        # country-level catch-alls for non-hub cities
        self.assertEqual(classify_city("Lyon, France"), "france")
        self.assertEqual(classify_city("Hamburg, Germany"), "germany")
        self.assertEqual(classify_city("Vienna, Austria"), "eu-other")

    def test_remote_variants(self):
        self.assertEqual(classify_city("Anywhere"), "remote-global")
        self.assertEqual(classify_city("Remote, Worldwide"), "remote-global")
        self.assertEqual(classify_city("Remote (EU)"), "remote-eu")
        # US roles are now kept (the user is open to roles abroad), not dropped.
        self.assertEqual(classify_city("Remote - US only"), "usa")
        self.assertEqual(classify_city("Remote (USA)"), "usa")


class TestRoleFamily(unittest.TestCase):
    def test_families(self):
        # Offensive security is the core of this profile and wins over generic swe.
        self.assertEqual(classify_role_family("Penetration Tester"), "offensive_security")
        self.assertEqual(classify_role_family("Red Team Operator"), "offensive_security")
        self.assertEqual(classify_role_family("Security Engineer, Red Team"), "offensive_security")
        self.assertEqual(classify_role_family("Application Security Engineer"), "appsec")
        self.assertEqual(classify_role_family("SOC Analyst"), "blue_team")
        self.assertEqual(classify_role_family("Cloud Security Engineer"), "cloud_grc")
        self.assertEqual(classify_role_family("Security Engineer"), "security_other")
        # non-security roles still classify (kept low priority), non-tech is None
        self.assertEqual(classify_role_family("Software Engineer, Backend"), "swe")
        self.assertEqual(classify_role_family("Machine Learning Engineer"), "ai_ml")
        self.assertIsNone(classify_role_family("Office Manager"))
        self.assertIsNone(classify_role_family("Account Executive"))


class TestStripHtml(unittest.TestCase):
    def test_strip(self):
        self.assertEqual(strip_html("<p>Hello&amp;<br/>world</p>"), "Hello& world")
        self.assertEqual(strip_html(""), "")
        self.assertEqual(strip_html(None), "")


class TestExtractApplyLink(unittest.TestCase):
    def test_prefers_a_link_that_mentions_apply(self):
        html_ = (
            '<p>Great role. <a href="https://company.com/about">About us</a></p>'
            '<p>Apply here: <a href="https://boards.greenhouse.io/co/jobs/123">link</a></p>'
        )
        self.assertEqual(extract_apply_link(html_), "https://boards.greenhouse.io/co/jobs/123")

    def test_falls_back_to_last_external_link(self):
        html_ = (
            '<a href="https://arbeitnow.com/jobs/x">this posting</a>'
            '<a href="https://company.com/careers/123">Careers page</a>'
        )
        self.assertEqual(extract_apply_link(html_, exclude_domain="arbeitnow.com"), "https://company.com/careers/123")

    def test_excludes_own_domain_and_social_links(self):
        html_ = (
            '<a href="https://arbeitnow.com/jobs/x">this posting</a>'
            '<a href="https://linkedin.com/company/co">LinkedIn</a>'
        )
        self.assertIsNone(extract_apply_link(html_, exclude_domain="arbeitnow.com"))

    def test_no_links_returns_none(self):
        self.assertIsNone(extract_apply_link("<p>No links here.</p>"))
        self.assertIsNone(extract_apply_link(""))
        self.assertIsNone(extract_apply_link(None))


if __name__ == "__main__":
    unittest.main()
