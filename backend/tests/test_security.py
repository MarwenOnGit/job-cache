import asyncio
import socket
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

import app as app_module
import http_util
import serve


def _call(path, headers=None, method="GET"):
    """Drive the ASGI app directly (no httpx needed); returns the status code."""
    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": method, "scheme": "http", "path": path, "raw_path": path.encode(),
        "root_path": "", "query_string": b"", "server": ("127.0.0.1", 8000),
        "client": ("127.0.0.1", 50000),
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
    }
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    asyncio.run(app_module.app(scope, receive, send))
    return next(m["status"] for m in sent if m["type"] == "http.response.start")


class TestLocalOnlyMiddleware(unittest.TestCase):
    # /api/materials 404s for an unknown id without touching the DB, so a 404
    # means "got past the middleware" and a 403 means "blocked by it".
    PATH = "/api/jobs/does-not-exist/materials"

    def test_loopback_hosts_are_allowed(self):
        for host in ("localhost:8000", "127.0.0.1:8000", "[::1]:8000", "localhost"):
            self.assertEqual(_call(self.PATH, {"Host": host}), 404, host)

    def test_foreign_host_is_rejected(self):
        # DNS rebinding: attacker's domain resolving to 127.0.0.1
        self.assertEqual(_call(self.PATH, {"Host": "evil.example:8000"}), 403)
        self.assertEqual(_call(self.PATH, {"Host": "192.168.1.20:8000"}), 403)
        self.assertEqual(_call(self.PATH, {}), 403)

    def test_same_origin_request_is_allowed(self):
        h = {"Host": "localhost:8000", "Origin": "http://localhost:8000",
             "Sec-Fetch-Site": "same-origin"}
        self.assertEqual(_call(self.PATH, h), 404)

    def test_typed_url_navigation_is_allowed(self):
        h = {"Host": "localhost:8000", "Sec-Fetch-Site": "none"}
        self.assertEqual(_call(self.PATH, h), 404)

    def test_cross_origin_api_request_is_rejected(self):
        h = {"Host": "localhost:8000", "Origin": "https://evil.example"}
        self.assertEqual(_call(self.PATH, h, method="POST"), 403)

    def test_other_local_port_is_rejected(self):
        h = {"Host": "localhost:8000", "Origin": "http://localhost:3000"}
        self.assertEqual(_call(self.PATH, h), 403)

    def test_sandboxed_frame_null_origin_is_rejected(self):
        h = {"Host": "localhost:8000", "Origin": "null", "Sec-Fetch-Site": "cross-site"}
        self.assertEqual(_call(self.PATH, h), 403)

    def test_cross_site_embed_without_origin_is_rejected(self):
        # e.g. <img src="http://localhost:8000/api/proxy?..."> on another site
        h = {"Host": "localhost:8000", "Sec-Fetch-Site": "cross-site"}
        self.assertEqual(_call(self.PATH, h), 403)


def _fake_resolve(ip):
    return lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443))]


class TestIsPublicUrl(unittest.TestCase):
    def test_public_ip_is_allowed(self):
        with patch("socket.getaddrinfo", _fake_resolve("93.184.216.34")):
            self.assertTrue(http_util.is_public_url("https://boards.greenhouse.io/x"))

    def test_private_and_special_addresses_are_rejected(self):
        for ip in ("127.0.0.1", "10.0.0.5", "192.168.1.1", "172.16.0.1",
                   "169.254.169.254", "0.0.0.0", "100.64.0.1", "::1", "fe80::1",
                   "::ffff:127.0.0.1", "224.0.0.1"):
            with patch("socket.getaddrinfo", _fake_resolve(ip)):
                self.assertFalse(http_util.is_public_url("http://example.com/"), ip)

    def test_any_private_answer_rejects_the_host(self):
        answers = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80)),
                   (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))]
        with patch("socket.getaddrinfo", lambda *a, **k: answers):
            self.assertFalse(http_util.is_public_url("http://example.com/"))

    def test_unresolvable_or_non_http_is_rejected(self):
        with patch("socket.getaddrinfo", side_effect=socket.gaierror):
            self.assertFalse(http_util.is_public_url("http://nope.invalid/"))
        self.assertFalse(http_util.is_public_url("file:///etc/passwd"))
        self.assertFalse(http_util.is_public_url("http:///nohost"))

    def test_redirect_to_private_address_is_refused(self):
        handler = http_util._PublicOnlyRedirect()
        req = urllib.request.Request("https://example.com/")
        with patch("socket.getaddrinfo", _fake_resolve("169.254.169.254")):
            with self.assertRaises(urllib.error.URLError):
                handler.redirect_request(req, None, 302, "Found", {},
                                         "http://169.254.169.254/latest/meta-data/")


class TestProxyGuards(unittest.TestCase):
    def test_proxy_refuses_internal_url_without_fetching(self):
        with patch("socket.getaddrinfo", _fake_resolve("127.0.0.1")), \
                patch("urllib.request.OpenerDirector.open") as m:
            with self.assertRaises(app_module.HTTPException) as ctx:
                app_module.proxy("http://localhost:8000/api/export")
        self.assertEqual(ctx.exception.status_code, 400)
        m.assert_not_called()

    def test_base_href_is_escaped(self):
        class _Resp:
            headers = {"Content-Type": "text/html"}
            def read(self): return b"<html><head></head><body>hi</body></html>"
            def __enter__(self): return self
            def __exit__(self, *a): return False

        url = 'https://example.com/a"><script>alert(1)</script>'
        with patch("socket.getaddrinfo", _fake_resolve("93.184.216.34")), \
                patch.object(http_util, "open_public", return_value=_Resp()):
            resp = app_module.proxy(url)
        body = bytes(resp.body).decode()
        self.assertNotIn("<script>alert(1)</script>", body)
        self.assertIn("&quot;&gt;&lt;script&gt;", body)


class TestServeBindsLoopbackOnly(unittest.TestCase):
    def test_sockets_are_loopback(self):
        socks = serve.make_loopback_sockets(0)
        try:
            addrs = {s.getsockname()[0] for s in socks}
            self.assertIn("127.0.0.1", addrs)
            self.assertTrue(addrs <= {"127.0.0.1", "::1"}, addrs)
        finally:
            for s in socks:
                s.close()


if __name__ == "__main__":
    unittest.main()
