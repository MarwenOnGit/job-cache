import unittest
import urllib.error
from unittest.mock import MagicMock, patch

import http_util


class _FakeResp:
    def __init__(self, status, headers):
        self.status = status
        self.headers = headers

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class TestResolveRedirect(unittest.TestCase):
    def test_redirect_returns_status_and_location(self):
        opener = MagicMock()
        opener.open.side_effect = urllib.error.HTTPError(
            "http://x", 302, "Found", {"Location": "https://real-ats.example.com/job/1"}, None)
        with patch("urllib.request.build_opener", return_value=opener):
            result = http_util.resolve_redirect("https://board.example.com/jobs/1/apply")
        self.assertEqual(result, (302, "https://real-ats.example.com/job/1"))

    def test_ok_response_returns_status_with_no_location(self):
        opener = MagicMock()
        opener.open.return_value = _FakeResp(200, {})
        with patch("urllib.request.build_opener", return_value=opener):
            result = http_util.resolve_redirect("https://board.example.com/jobs/1/apply")
        self.assertEqual(result, (200, None))

    def test_not_found_returns_status(self):
        opener = MagicMock()
        opener.open.side_effect = urllib.error.HTTPError("http://x", 404, "Not Found", {}, None)
        with patch("urllib.request.build_opener", return_value=opener):
            result = http_util.resolve_redirect("https://board.example.com/jobs/dead/apply")
        self.assertEqual(result, (404, None))

    def test_network_failure_returns_none(self):
        opener = MagicMock()
        opener.open.side_effect = urllib.error.URLError("no route to host")
        with patch("urllib.request.build_opener", return_value=opener):
            result = http_util.resolve_redirect("https://unreachable.example.com/apply")
        self.assertIsNone(result)

    def test_timeout_returns_none(self):
        opener = MagicMock()
        opener.open.side_effect = TimeoutError()
        with patch("urllib.request.build_opener", return_value=opener):
            result = http_util.resolve_redirect("https://slow.example.com/apply")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
