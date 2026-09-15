"""Minimal HTTP JSON helper built on the stdlib (no third-party deps)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Optional

_UA = "job-hunter/1.0 (+https://github.com/samiimasmoudii)"


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
