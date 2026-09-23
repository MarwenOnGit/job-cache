import json
import unittest
from unittest.mock import patch

import app as app_module


class TestIsKnownNonEmbeddable(unittest.TestCase):
    def test_ashby_is_non_embeddable(self):
        self.assertTrue(app_module._is_known_non_embeddable(
            "https://jobs.ashbyhq.com/vibe/45d3/application"))

    def test_workday_is_non_embeddable(self):
        self.assertTrue(app_module._is_known_non_embeddable(
            "https://acme.wd5.myworkdayjobs.com/en-US/careers/job/1"))

    def test_ordinary_ats_is_embeddable(self):
        self.assertFalse(app_module._is_known_non_embeddable(
            "https://boards.greenhouse.io/acme/jobs/1"))
        self.assertFalse(app_module._is_known_non_embeddable(
            "https://jobs.lever.co/acme/1"))


class TestProxyEndpoint(unittest.TestCase):
    def test_non_embeddable_host_short_circuits_without_a_network_call(self):
        with patch("urllib.request.urlopen") as m:
            resp = app_module.proxy("https://jobs.ashbyhq.com/vibe/45d3/application")
        m.assert_not_called()
        self.assertEqual(resp.status_code, 502)
        body = json.loads(bytes(resp.body))
        self.assertFalse(body["ok"])


if __name__ == "__main__":
    unittest.main()
