import structlog

from app.ai.client import ARTIST_EXTRACTOR_PROMPT
from app.ai.extractors.base import BaseExtractor

logger = structlog.get_logger()


class ArtistExtractor(BaseExtractor):
    record_type = "artist"
    system_prompt = ARTIST_EXTRACTOR_PROMPT

    async def extract(self, url: str, html: str, context: dict | None = None) -> dict:
        preprocessed = self.preprocess_html(html)
        image_urls = self.extract_image_urls(html, url)

        response = await self.ai_client.complete(
            system_prompt=self.system_prompt,
            user_content=self._build_user_content(url, preprocessed, context=context),
            response_format={"type": "json_object"},
        )

        existing_images = response.get("image_urls", [])
        all_images = list(dict.fromkeys([*existing_images, *image_urls]))
        response["image_urls"] = all_images

        for field in ("mediums", "collections"):
            if not isinstance(response.get(field), list):
                response[field] = []
        for text_field in ("bio", "about", "phone"):
            value = response.get(text_field)
            if value is None:
                continue
            response[text_field] = str(value).strip() or None
        for list_field in ("news_items", "exhibitions", "page_image_candidates", "art_classes"):
            value = response.get(list_field)
            if not isinstance(value, list):
                response[list_field] = []
                continue
            normalized = []
            for item in value:
                if isinstance(item, dict):
                    normalized.append(item)
                elif item not in (None, ""):
                    normalized.append({"value": str(item).strip()})
            response[list_field] = normalized

        return response
