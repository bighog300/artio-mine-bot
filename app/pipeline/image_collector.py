import asyncio
import re
from urllib.parse import urlparse

import httpx
import structlog
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.db.models import Image

logger = structlog.get_logger()

PROFILE_KEYWORDS = {"portrait", "headshot", "avatar", "profile", "author", "artist-photo"}
ARTWORK_KEYWORDS = {"artwork", "painting", "sculpture", "drawing", "artwork", "canvas"}
POSTER_KEYWORDS = {"poster", "exhibition", "event", "banner", "flyer"}
VENUE_KEYWORDS = {"venue", "gallery", "exterior", "interior", "building", "museum"}

TRACKING_DOMAINS = {
    "google-analytics.com",
    "googletagmanager.com",
    "facebook.com",
    "doubleclick.net",
    "analytics.",
    "pixel.",
}


def _classify_image(url: str, alt: str, context_text: str, img_tag) -> tuple[str, int]:
    """Classify image type and return (type, confidence)."""
    url_lower = url.lower()
    alt_lower = (alt or "").lower()
    ctx_lower = (context_text or "").lower()

    # Get class attributes if available
    classes = " ".join(img_tag.get("class", []) if img_tag else []).lower()
    combined = f"{alt_lower} {classes} {url_lower}"

    if any(kw in combined for kw in PROFILE_KEYWORDS):
        return "profile", 85

    if any(kw in combined for kw in ARTWORK_KEYWORDS):
        return "artwork", 80

    if any(kw in ctx_lower for kw in POSTER_KEYWORDS):
        return "poster", 70

    if any(kw in combined for kw in VENUE_KEYWORDS):
        return "venue", 75

    return "unknown", 50


def _extract_images_from_html(html: str, base_url: str) -> list[dict]:
    """Extract image data from HTML with context."""
    from urllib.parse import urljoin

    soup = BeautifulSoup(html, "lxml")
    images = []
    seen: set[str] = set()

    for img in soup.find_all("img"):
        for attr in ("src", "data-src", "data-lazy-src", "data-original"):
            src = img.get(attr, "").strip()
            if not src or src.startswith("data:"):
                continue
            full_url = urljoin(base_url, src)
            if full_url in seen:
                continue

            # Filter noise
            parsed = urlparse(full_url)
            domain = parsed.netloc.lower()
            if any(td in domain for td in TRACKING_DOMAINS):
                continue

            ext = full_url.rsplit(".", 1)[-1].lower() if "." in full_url else ""
            if ext in ("svg", "ico", "gif"):
                continue

            # Get dimensions from attributes
            width = None
            height = None
            try:
                w = img.get("width", "")
                h = img.get("height", "")
                if w:
                    width = int(re.sub(r"[^\d]", "", str(w)) or "0") or None
                if h:
                    height = int(re.sub(r"[^\d]", "", str(h)) or "0") or None
            except (ValueError, TypeError):
                pass

            # Skip known tiny images
            if width and height and (width < 100 or height < 100):
                continue

            alt = img.get("alt", "")
            # Get surrounding text for context
            parent = img.parent
            ctx = parent.get_text(strip=True) if parent else ""

            seen.add(full_url)
            images.append(
                {
                    "url": full_url,
                    "alt": alt,
                    "width": width,
                    "height": height,
                    "context": ctx,
                    "img_tag": img,
                }
            )

    return images


async def collect_images(
    record_id: str,
    page_url: str,
    html: str,
    image_urls: list[str],
    db: AsyncSession,
    source_id: str,
    page_id: str | None = None,
) -> list[Image]:
    """Collect and validate images for a record, creating Image records in DB."""
    raw_images = _extract_images_from_html(html, page_url)

    # Merge with additional image_urls from extraction
    seen: set[str] = {img["url"] for img in raw_images}
    for url in image_urls:
        if url not in seen:
            seen.add(url)
            raw_images.append(
                {"url": url, "alt": "", "width": None, "height": None, "context": "", "img_tag": None}
            )

    results: list[Image] = []

    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        for img_data in raw_images:
            url = img_data["url"]
            try:
                resp = await client.head(url)
                content_type = resp.headers.get("content-type", "")
                is_valid = resp.status_code < 400 and content_type.startswith("image/")
                mime_type = content_type.split(";")[0].strip() if is_valid else None
            except Exception as exc:
                logger.debug("image_head_failed", url=url, error=str(exc))
                is_valid = False
                mime_type = None

            if not is_valid:
                continue

            alt = img_data["alt"]
            ctx = img_data["context"]
            img_tag = img_data["img_tag"]

            image_type, confidence = _classify_image(url, alt, ctx, img_tag)

            try:
                image = await crud.create_image(
                    db,
                    source_id=source_id,
                    url=url,
                    record_id=record_id,
                    page_id=page_id,
                    alt_text=alt or None,
                    image_type=image_type,
                    width=img_data.get("width"),
                    height=img_data.get("height"),
                    mime_type=mime_type,
                    is_valid=True,
                    confidence=confidence,
                )
                results.append(image)
            except Exception as exc:
                logger.debug("image_create_failed", url=url, error=str(exc))

    return results
