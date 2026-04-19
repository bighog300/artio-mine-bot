import time
from typing import Any

import structlog
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.runtime_ai_policy import assert_ai_allowed

logger = structlog.get_logger()

PAGE_CLASSIFIER_PROMPT = """You classify web pages from art websites into one of these types:
- artist_profile: A page dedicated to one specific artist with bio and/or portfolio
- event_detail: A single event or show with title, dates, and venue
- exhibition_detail: A single exhibition with title, dates, and description
- venue_profile: A gallery or museum page with description and contact info
- artwork_detail: A single artwork listing with title, medium, and image
- artist_directory: An index listing multiple artists (A-Z or paginated)
- event_listing: An index listing multiple upcoming or past events
- exhibition_listing: An index listing multiple exhibitions
- artwork_listing: A grid of artworks for sale or display
- category: A general category or navigation page
- unknown: Cannot determine from the content provided

Return JSON only:
{
  "page_type": "<type>",
  "confidence": <0-100>,
  "reasoning": "<one sentence>"
}

Rules:
- Return exactly one type
- Base decision only on the HTML content provided
- Confidence 80+ = certain, 50-79 = probable, below 50 = uncertain
- If page is a 404, login wall, or broken return unknown with confidence 0"""

EVENT_EXTRACTOR_PROMPT = """Extract structured data from this art event or exhibition page.
Return ONLY valid JSON matching this exact schema. Use null for missing fields.
Do not invent information not present on the page.

Schema:
{
  "title": "string — event title",
  "description": "string | null — event description",
  "start_date": "string | null — ISO date e.g. 2026-04-15",
  "end_date": "string | null — ISO date",
  "venue_name": "string | null",
  "venue_address": "string | null",
  "artist_names": ["string"],
  "ticket_url": "string | null — full URL",
  "is_free": "boolean | null",
  "price_text": "string | null — raw price string",
  "image_urls": ["string"]
}"""

ARTIST_EXTRACTOR_PROMPT = """Extract structured data from this artist profile page.
Return ONLY valid JSON. Use null for missing fields. Do not invent.

Schema:
{
  "name": "string — artist full name",
  "bio": "string | null — biographical text",
  "nationality": "string | null",
  "birth_year": "integer | null",
  "mediums": ["string"],
  "website_url": "string | null — full URL",
  "instagram_url": "string | null — full URL",
  "email": "string | null",
  "collections": ["string"],
  "avatar_url": "string | null — URL of artist portrait photo NOT artwork",
  "image_urls": ["string"]
}"""

EXHIBITION_EXTRACTOR_PROMPT = """Extract structured data from this art exhibition page.
Return ONLY valid JSON. Use null for missing fields. Do not invent.

Schema:
{
  "title": "string — exhibition title",
  "description": "string | null",
  "start_date": "string | null — ISO date",
  "end_date": "string | null — ISO date",
  "venue_name": "string | null",
  "artist_names": ["string"],
  "curator": "string | null",
  "image_urls": ["string"]
}"""

VENUE_EXTRACTOR_PROMPT = """Extract structured data from this art gallery or venue page.
Return ONLY valid JSON. Use null for missing fields. Do not invent.

Schema:
{
  "name": "string — venue or gallery name",
  "description": "string | null",
  "address": "string | null",
  "city": "string | null",
  "country": "string | null",
  "website_url": "string | null",
  "phone": "string | null",
  "email": "string | null",
  "opening_hours": "string | null",
  "image_urls": ["string"]
}"""

ARTWORK_EXTRACTOR_PROMPT = """Extract structured data from this artwork page.
Return ONLY valid JSON. Use null for missing fields. Do not invent.

Schema:
{
  "title": "string — artwork title",
  "artist_name": "string | null",
  "medium": "string | null — e.g. Oil on canvas",
  "year": "integer | null",
  "dimensions": "string | null — e.g. 90 x 120 cm",
  "description": "string | null",
  "price": "string | null — raw price string",
  "image_urls": ["string"]
}"""

SITE_MAPPER_PROMPT = """Analyse this art website homepage and identify all content sections.
Return ONLY valid JSON.

Schema:
{
  "platform": "string — wordpress | squarespace | custom | unknown",
  "sections": [
    {
      "name": "string — human readable name e.g. Artists A-Z",
      "url": "string — full section base URL",
      "content_type": "artist_directory | event_listing | exhibition_listing | artwork_listing | venue_profile | unknown",
      "pagination_type": "letter | numbered | none",
      "index_pattern": "string | null — URL with [letter] or [page] placeholder",
      "confidence": 0-100
    }
  ]
}

Rules:
- Only include sections you can see navigation links for
- Do not invent sections not linked from the page
- For letter-paginated directories use [letter] placeholder
- For numbered pages use [page] placeholder"""


class AIExtractionError(Exception):
    pass


class OpenAIClient:
    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def complete(
        self,
        system_prompt: str,
        user_content: str,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        assert_ai_allowed("openai.complete")
        start = time.time()
        kwargs: dict[str, Any] = {
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        }
        if response_format:
            kwargs["response_format"] = response_format

        try:
            response = await self._client.chat.completions.create(**kwargs)
            duration = time.time() - start
            usage = response.usage
            logger.info(
                "openai_call",
                model=settings.openai_model,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                duration_s=round(duration, 2),
            )
            content = response.choices[0].message.content
            if content is None:
                raise AIExtractionError("Empty response from OpenAI")
            import json

            return json.loads(content)
        except Exception as exc:
            logger.error("openai_error", error=str(exc))
            raise AIExtractionError(str(exc)) from exc
