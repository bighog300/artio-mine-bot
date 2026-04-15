import hashlib
import re
from collections.abc import Iterable
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup


YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")
DATE_RE = re.compile(
    r"\b(?:\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}|\d{4})\b"
)


def _iter_blocks(soup: BeautifulSoup) -> Iterable[Any]:
    for selector in ("li", "article", "p"):
        for node in soup.select(selector):
            text = node.get_text(" ", strip=True)
            if len(text) >= 8:
                yield node


def _parse_year_range(text: str) -> tuple[int | None, int | None]:
    years = [int(y) for y in YEAR_RE.findall(text)]
    if not years:
        return None, None
    if len(years) == 1:
        return years[0], years[0]
    return min(years), max(years)


def _extract_date_text(text: str) -> str | None:
    matches = DATE_RE.findall(text)
    if not matches:
        return None
    return " - ".join(matches[:2])


def _fingerprint(page_url: str, raw_text: str) -> str:
    return hashlib.sha1(f"{page_url}|{raw_text}".encode("utf-8")).hexdigest()


def _extract_common_link(node: Any, source_url: str) -> str | None:
    link = node.find("a", href=True)
    if link:
        return urljoin(source_url, link.get("href"))
    return None


def _extract_publication_date(text: str) -> str | None:
    date_text = _extract_date_text(text)
    if not date_text:
        return None
    match = re.search(r"(19\d{2}|20\d{2})", date_text)
    if match:
        return f"{match.group(1)}-01-01"
    return None


def extract_artist_related_items(page_type: str, html: str, source_url: str) -> dict[str, list[dict[str, Any]]]:
    soup = BeautifulSoup(html, "lxml")

    if page_type == "artist_exhibitions":
        items = []
        for node in _iter_blocks(soup):
            raw_text = node.get_text(" ", strip=True)
            if len(raw_text) < 12:
                continue
            year_start, year_end = _parse_year_range(raw_text)
            date_text = _extract_date_text(raw_text)
            title = node.find(["strong", "b", "h3", "h4"])
            items.append(
                {
                    "raw_text": raw_text,
                    "title": title.get_text(" ", strip=True) if title else raw_text.split(",")[0][:160],
                    "venue": None,
                    "city": None,
                    "country": None,
                    "date_text": date_text,
                    "year_start": year_start,
                    "year_end": year_end,
                    "exhibition_type": "exhibition",
                    "solo_or_group": "solo" if "solo" in raw_text.lower() else None,
                    "source_url": source_url,
                    "item_fingerprint": _fingerprint(source_url, raw_text),
                }
            )
        return {"exhibitions": items}

    if page_type == "artist_articles":
        items = []
        for node in _iter_blocks(soup):
            raw_text = node.get_text(" ", strip=True)
            if len(raw_text) < 12:
                continue
            title = node.find(["strong", "b", "h3", "h4", "a"])
            items.append(
                {
                    "raw_text": raw_text,
                    "title": title.get_text(" ", strip=True) if title else raw_text[:160],
                    "author": None,
                    "publication": None,
                    "publication_date": _extract_publication_date(raw_text),
                    "url": _extract_common_link(node, source_url),
                    "source_url": source_url,
                    "item_fingerprint": _fingerprint(source_url, raw_text),
                }
            )
        return {"articles": items}

    if page_type == "artist_press":
        items = []
        for node in _iter_blocks(soup):
            raw_text = node.get_text(" ", strip=True)
            if len(raw_text) < 12:
                continue
            title = node.find(["strong", "b", "h3", "h4", "a"])
            items.append(
                {
                    "raw_text": raw_text,
                    "title": title.get_text(" ", strip=True) if title else raw_text[:160],
                    "publication": None,
                    "publication_date": _extract_publication_date(raw_text),
                    "author": None,
                    "url": _extract_common_link(node, source_url),
                    "source_url": source_url,
                    "item_fingerprint": _fingerprint(source_url, raw_text),
                }
            )
        return {"press": items}

    if page_type == "artist_memories":
        items = []
        for node in _iter_blocks(soup):
            raw_text = node.get_text(" ", strip=True)
            if len(raw_text) < 12:
                continue
            items.append(
                {
                    "raw_text": raw_text,
                    "title": raw_text[:120],
                    "source_url": source_url,
                    "item_fingerprint": _fingerprint(source_url, raw_text),
                    "captured_at": datetime.utcnow().isoformat(),
                }
            )
        return {"memories": items}

    return {}
