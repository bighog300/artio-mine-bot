import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.source_mapper.mapping_suggestion import build_mapping_json


class MappingSuggestionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_draft(self, source_id: str, profile_id: str):
        families = await crud.list_url_families(self.db, profile_id)
        family_payload = [
            {
                "family_key": family.family_key,
                "path_pattern": family.path_pattern,
                "page_type_candidate": family.page_type_candidate,
                "confidence": float(family.confidence),
                "sample_urls": json.loads(family.sample_urls_json or "[]"),
                "diagnostics": json.loads(family.diagnostics_json or "{}"),
            }
            for family in families
        ]
        mapping_json = build_mapping_json(source_id, profile_id, family_payload)
        return await crud.create_mapping_suggestion_draft(
            self.db,
            source_id=source_id,
            profile_id=profile_id,
            mapping_json=mapping_json,
            created_by="admin",
        )
