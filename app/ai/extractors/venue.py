import structlog

from app.ai.client import VENUE_EXTRACTOR_PROMPT
from app.ai.extractors.base import BaseExtractor

logger = structlog.get_logger()


class VenueExtractor(BaseExtractor):
    record_type = "venue"
    system_prompt = VENUE_EXTRACTOR_PROMPT

    async def extract(self, url: str, html: str) -> dict:
        preprocessed = self.preprocess_html(html)
        image_urls = self.extract_image_urls(html, url)

        response = await self.ai_client.complete(
            system_prompt=self.system_prompt,
            user_content=f"URL: {url}\n\nHTML:\n{preprocessed}",
            response_format={"type": "json_object"},
        )

        existing_images = response.get("image_urls", [])
        all_images = list(dict.fromkeys(existing_images + image_urls))
        response["image_urls"] = all_images

        return response
