"""Minimal HTTP JSON helper built on the stdlib (no third-party deps)."""
from __future__ import annotations

import http.client
import ipaddress
import json
import socket
import urllib.error
import urllib.request
from typing import Any, Optional, Tuple
from urllib.parse import urlparse

_UA = "job-cache/1.0 (+https://github.com/MarwenOnGit/job-cache)"


def get_json(url: str, timeout: int = 20, headers: Optional[dict] = None) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def post_json(url: str, payload: dict, timeout: int = 20, headers: Optional[dict] = None) -> Any:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"User-Agent": _UA, "Accept": "application/json",
                 "Content-Type": "application/json", **(headers or {})},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None  # decline to follow — surfaces the 3xx as an HTTPError instead


def resolve_redirect(url: str, timeout: int = 8) -> Optional[Tuple[int, Optional[str]]]:
    """Probe a URL WITHOUT following any redirect, and without downloading a real
    destination page's body. Returns (status_code, Location_header_or_None) for
    any response the server actually sends back, or None if the request itself
    couldn't be made at all (DNS failure, timeout, connection refused, ...).

    Some job boards (Arbeitnow) don't put the employer's real application link
    in the posting anywhere — their own "Apply" button is a same-site tracking
    URL that 302s to the real ATS. This resolves that one hop cheaply so we can
    store the real destination instead of the board's own redirect link.
    """
    # The URL comes from harvested data: same public-only + pinned-connection
    # rules as the Apply-workspace proxy (see open_public below).
    if not is_public_url(url):
        return None
    opener = urllib.request.build_opener(_NoRedirect, _PinnedHTTPHandler, _PinnedHTTPSHandler)
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        with opener.open(req, timeout=timeout) as resp:
            return resp.status, resp.headers.get("Location")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location")
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


# --- fetching untrusted URLs (the Apply-workspace proxy) ---------------------
# Job postings come from open aggregators, so their apply links are untrusted.
# Before fetching one on the user's behalf, make sure it (and every redirect hop)
# points at the public internet, not at this machine, the LAN, or a cloud
# metadata endpoint.

def _is_public_ip(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value.split("%", 1)[0])  # drop an IPv6 zone id
    except ValueError:
        return False
    if ip.version == 6 and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


def is_public_url(url: str) -> bool:
    """True only for an http(s) URL whose host resolves exclusively to public IPs."""
    try:
        parsed = urlparse(url)
        host, port = parsed.hostname, parsed.port
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https") or not host:
        return False
    try:
        infos = socket.getaddrinfo(host, port or (443 if parsed.scheme == "https" else 80),
                                   proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError, OSError):
        return False
    return bool(infos) and all(_is_public_ip(info[4][0]) for info in infos)


class _PublicOnlyRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not is_public_url(newurl):
            raise urllib.error.URLError("redirect to a non-public address")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _create_public_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
    """socket.create_connection() that resolves the host ONCE, refuses if any
    answer isn't public, and connects to exactly those checked IPs. Checking a
    URL up front and letting the connection resolve the name again would leave
    a DNS-rebinding gap (public on the check, 127.0.0.1 on the connect)."""
    host, port = address
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not infos or not all(_is_public_ip(info[4][0]) for info in infos):
        raise OSError(f"refusing to connect to non-public address for {host!r}")
    last_err: Optional[OSError] = None
    for info in infos:
        try:
            return socket.create_connection(info[4][:2], timeout, source_address)
        except OSError as e:
            last_err = e
    raise last_err or OSError(f"could not connect to {host!r}")


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_connection = _create_public_connection


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    # Only the TCP connect is pinned: TLS still verifies the certificate against
    # the real hostname (SNI + check_hostname use self.host), and the Host header
    # comes from the request as usual.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_connection = _create_public_connection


def _proxied(req: urllib.request.Request) -> bool:
    # Through a configured proxy, the proxy resolves the target, so there is no
    # local connection to pin; the up-front is_public_url() check still applies.
    return req.has_proxy() or bool(getattr(req, "_tunnel_host", None))


class _PinnedHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return super().http_open(req) if _proxied(req) else self.do_open(_PinnedHTTPConnection, req)


class _PinnedHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        if _proxied(req):
            return super().https_open(req)
        return self.do_open(_PinnedHTTPSConnection, req, context=self._context)


def open_public(req: urllib.request.Request, timeout: int = 12):
    """urlopen() that refuses non-public destinations, including via redirects,
    and connects to the same IPs it validated (no DNS-rebinding window).
    Raises urllib.error.URLError when the URL or a redirect hop isn't public."""
    if not is_public_url(req.full_url):
        raise urllib.error.URLError("not a public address")
    opener = urllib.request.build_opener(_PublicOnlyRedirect, _PinnedHTTPHandler, _PinnedHTTPSHandler)
    return opener.open(req, timeout=timeout)
