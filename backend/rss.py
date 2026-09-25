"""Tiny stdlib RSS 2.0 / Atom reader: feed text -> list of {title, link, text, published}."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List, Optional

from normalize import strip_html

_ATOM = "{http://www.w3.org/2005/Atom}"
_CONTENT = "{http://purl.org/rss/1.0/modules/content/}encoded"


def _first(el: ET.Element, *tags: str) -> str:
    for tag in tags:
        child = el.find(tag)
        if child is not None and (child.text or "").strip():
            return child.text.strip()
    return ""


def _date(value: str) -> Optional[str]:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return None


def parse(xml_text: str) -> List[dict]:
    try:
        root = ET.fromstring((xml_text or "").lstrip("﻿").strip())
    except ET.ParseError:
        return []
    entries = root.findall(".//item") or root.findall(f".//{_ATOM}entry")
    items: List[dict] = []
    for e in entries:
        title = strip_html(_first(e, "title", f"{_ATOM}title"))
        link = _first(e, "link")
        if not link:
            atom_link = e.find(f"{_ATOM}link")
            link = atom_link.get("href", "") if atom_link is not None else ""
        body = _first(e, _CONTENT, "description", f"{_ATOM}content", f"{_ATOM}summary")
        published = _date(_first(e, "pubDate", f"{_ATOM}published", f"{_ATOM}updated"))
        if title and link:
            items.append({"title": title, "link": link.strip(),
                          "text": strip_html(body), "published": published})
    return items
