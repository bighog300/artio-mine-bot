import json
from abc import ABC, abstractmethod
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.ai.client import AIExtractionError, OpenAIClient

# Domains/patterns to filter out (tracking pixels, logos, icons)
NOISE_DOMAINS = {
    "google-analytics.com",
    "googletagmanager.com",
    "facebook.com",
    "doubleclick.net",
    "ad.doubleclick.net",
    "analytics.",
    "pixel.",
}

NOISE_EXTENSIONS = {".svg", ".ico", ".gif"}
NOISE_KEYWORDS = ["logo", "icon", "spinner", "placeholder", "blank", "pixel", "1x1", "tracking"]


class BaseExtractor(ABC):
    record_type: str = ""
    system_prompt: str = ""

    def __init__(self, ai_client: OpenAIClient) -> None:
        self.ai_client = ai_client

    def preprocess_html(self, html: str) -> str:
        """Strip noise elements and truncate to 8000 chars."""
        soup = BeautifulSoup(html, "lxml")
        for tag in soup.find_all(["script", "style", "nav", "footer", "noscript", "iframe"]):
            tag.decompose()
        # Remove ads and tracking
        for tag in soup.find_all(attrs={"class": lambda c: c and any(
            kw in " ".join(c).lower() for kw in ["ad-", "ads", "tracking", "cookie", "popup"]
        )}):
            tag.decompose()
        result = str(soup)[:8000]
        return result

    def extract_image_urls(self, html: str, base_url: str) -> list[str]:
        """Find all image URLs, filter noise, resolve relative URLs."""
        soup = BeautifulSoup(html, "lxml")
        urls: list[str] = []
        seen: set[str] = set()

        for img in soup.find_all("img"):
            for attr in ("src", "data-src", "data-lazy-src", "data-original"):
                src = img.get(attr, "").strip()
                if not src or src.startswith("data:"):
                    continue
                # Resolve relative URLs
                full_url = urljoin(base_url, src)
                if full_url in seen:
                    continue

                # Filter noise
                parsed = urlparse(full_url)
                domain = parsed.netloc.lower()
                path = parsed.path.lower()

                # Filter noise domains
                if any(nd in domain for nd in NOISE_DOMAINS):
                    continue

                # Filter noise extensions
                ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""
                if ext in NOISE_EXTENSIONS:
                    continue

                # Filter noise keywords in URL
                url_lower = full_url.lower()
                if any(kw in url_lower for kw in NOISE_KEYWORDS):
                    continue

                seen.add(full_url)
                urls.append(full_url)

        return urls

    def _build_user_content(self, url: str, html: str, context: dict | None = None) -> str:
        context_block = ""
        if context:
            context_block = f"\n\nContext hints:\n{json.dumps(context)}"
        return f"URL: {url}\n\nHTML:\n{html}{context_block}"

    @abstractmethod
    async def extract(self, url: str, html: str, context: dict | None = None) -> dict:
        """Extract structured data from page HTML."""
        ...
