import asyncio
import re
from urllib.parse import urlparse

import httpx
import structlog
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
logger = structlog.get_logger()

PROFILE_KEYWORDS = {"portrait", "headshot", "avatar", "profile", "author", "artist-photo"}
ARTWORK_KEYWORDS = {"artwork", "painting", "sculpture", "drawing", "artwork", "canvas"}
DECORATIVE_KEYWORDS = {"poster", "exhibition", "event", "banner", "flyer", "icon", "logo", "sprite"}
TEMPLATE_KEYWORDS = {"header", "footer", "nav", "menu", "background"}

TRACKING_DOMAINS = {
    "google-analytics.com",
    "googletagmanager.com",
    "facebook.com",
    "doubleclick.net",
    "analytics.",
    "pixel.",
}


def _classify_image(url: str, alt: str, context_text: str, img_tag, *, occurrence_count: int) -> tuple[str, int, str]:
    """Classify image role and return (role, confidence, reason)."""
    url_lower = url.lower()
    alt_lower = (alt or "").lower()
    ctx_lower = (context_text or "").lower()

    # Get class attributes if available
    classes = " ".join(img_tag.get("class", []) if img_tag else []).lower()
    combined = f"{alt_lower} {classes} {url_lower}"

    if any(kw in combined for kw in PROFILE_KEYWORDS):
        return "profile", 88, "keyword_profile"

    if any(kw in combined for kw in ARTWORK_KEYWORDS):
        return "artwork", 82, "keyword_artwork"

    if "artist" in ctx_lower and "photo" in ctx_lower:
        return "artist_photo", 78, "context_artist_photo"

    classes = " ".join(img_tag.get("class", []) if img_tag else []).lower()
    if any(zone in classes for zone in ("header", "footer", "nav", "menu", "sidebar")):
        return "template_shared", 74, "dom_zone_template"

    if any(kw in combined for kw in TEMPLATE_KEYWORDS):
        return "template_shared", 72, "keyword_template"

    if any(kw in (combined + " " + ctx_lower) for kw in DECORATIVE_KEYWORDS):
        return "decorative", 70, "decorative_context"

    if occurrence_count > 1:
        return "template_shared", 68, "repeated_across_page"

    return "unknown", 50, "fallback_unknown"


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
) -> list[dict]:
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

    results: list[dict] = []
    url_counts: dict[str, int] = {}
    for item in raw_images:
        url_counts[item["url"]] = url_counts.get(item["url"], 0) + 1

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

            image_type, confidence, reason = _classify_image(
                url, alt, ctx, img_tag, occurrence_count=url_counts.get(url, 1)
            )
            keep = image_type in {"profile", "artist_photo", "artwork"}

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
                results.append(
                    {
                        "url": url,
                        "role": image_type,
                        "confidence": confidence,
                        "keep": keep,
                        "reason": reason,
                        "image_id": image.id,
                    }
                )
            except Exception as exc:
                logger.debug("image_create_failed", url=url, error=str(exc))

    return results
