import structlog

from app.ai.client import EVENT_EXTRACTOR_PROMPT
from app.ai.extractors.base import BaseExtractor

logger = structlog.get_logger()


class EventExtractor(BaseExtractor):
    record_type = "event"
    system_prompt = EVENT_EXTRACTOR_PROMPT

    async def extract(self, url: str, html: str, context: dict | None = None) -> dict:
        preprocessed = self.preprocess_html(html)
        image_urls = self.extract_image_urls(html, url)

        response = await self.ai_client.complete(
            system_prompt=self.system_prompt,
            user_content=self._build_user_content(url, preprocessed, context=context),
            response_format={"type": "json_object"},
        )

        # Ensure required fields
        if not response.get("title"):
            logger.warning("event_extract_no_title", url=url)

        # Merge image URLs found directly
        existing_images = response.get("image_urls", [])
        all_images = list(dict.fromkeys(existing_images + image_urls))
        response["image_urls"] = all_images

        # Ensure array fields are lists
        if not isinstance(response.get("artist_names"), list):
            response["artist_names"] = []

        return response
