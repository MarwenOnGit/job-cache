"""Minimal HTTP JSON helper built on the stdlib (no third-party deps)."""
from __future__ import annotations

import ipaddress
import json
import socket
import urllib.error
import urllib.request
from typing import Any, Optional, Tuple
from urllib.parse import urlparse

_UA = "job-cache/1.0 (+https://github.com/samiimasmoudii)"


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
    opener = urllib.request.build_opener(_NoRedirect)
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


def open_public(req: urllib.request.Request, timeout: int = 12):
    """urlopen() that refuses non-public destinations, including via redirects.
    Raises urllib.error.URLError when the URL or a redirect hop isn't public."""
    if not is_public_url(req.full_url):
        raise urllib.error.URLError("not a public address")
    return urllib.request.build_opener(_PublicOnlyRedirect).open(req, timeout=timeout)
