"""Minimal HTTP JSON helper built on the stdlib (no third-party deps)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Optional, Tuple

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
