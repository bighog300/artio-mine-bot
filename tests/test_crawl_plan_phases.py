import json

import pytest

from app.db import crud
from app.db.models import SourceMappingPresetRow


def test_phases_for_page_types_art_co_za_shape():
    page_types = {
        "artist_directory_root",
        "artist_directory_letter",
        "artist_profile_hub",
        "artist_biography",
        "artist_related_page",
        "event_detail",
        "exhibition_detail",
        "venue_detail",
        "artwork_detail",
    }

    phases = crud._phases_for_page_types("https://art.co.za", page_types)
    phase_names = [phase["phase_name"] for phase in phases]

    assert phase_names == [
        "root",
        "artist_directory",
        "artist_directory_letters",
        "artist_profiles",
        "events",
        "exhibitions",
        "venues",
        "artworks",
    ]
    assert all(isinstance(phase.get("num_pages"), int) and phase["num_pages"] > 0 for phase in phases)


def test_build_runtime_map_from_preset_rows_generates_non_empty_phases():
    preset = crud.SourceMappingPreset(source_id="source-1", tenant_id="public", name="preset-a")
    rows = [
        SourceMappingPresetRow(
            preset_id="preset-1",
            page_type_key="artist_directory_root",
            page_type_label="Artist Directory Root",
            selector=".artists a",
            destination_field="source_url",
            is_enabled=True,
        ),
    ]

    runtime_map = crud.build_runtime_map_from_preset_rows(
        preset,
        rows,
        source_url="https://art.co.za",
    )

    phases = runtime_map.get("crawl_plan", {}).get("phases", [])
    assert phases
    assert phases[0]["phase_name"] == "root"
    assert phases[0]["base_url"] == "https://art.co.za"


def test_has_usable_runtime_map_payload_requires_non_empty_crawl_phases():
    assert crud.has_usable_runtime_map_payload({"crawl_plan": {"phases": []}}) is False
    assert (
        crud.has_usable_runtime_map_payload(
            {
                "crawl_plan": {
                    "phases": [
                        {"phase_name": "root", "base_url": "https://art.co.za", "url_pattern": "/", "pagination_type": "none", "num_pages": 1}
                    ]
                }
            }
        )
        is True
    )


@pytest.mark.asyncio
async def test_apply_source_mapping_preset_to_source_persists_runtime_map_phases(db_session):
    source = await crud.create_source(db_session, url="https://art.co.za", name="Art")
    preset = await crud.create_source_mapping_preset(
        db_session,
        source_id=source.id,
        tenant_id="public",
        name="preset-runtime",
        description=None,
        created_from_mapping_version_id=None,
        created_by=None,
        row_count=1,
        page_type_count=1,
    )
    db_session.add(
        SourceMappingPresetRow(
            preset_id=preset.id,
            page_type_key="artist_directory_letter",
            page_type_label="Artist Directory Letter",
            selector=".directory a",
            destination_field="source_url",
            is_enabled=True,
            sort_order=1,
        )
    )
    await db_session.commit()

    updated_source = await crud.apply_source_mapping_preset_to_source(
        db_session,
        source_id=source.id,
        preset_id=preset.id,
        tenant_id="public",
    )

    runtime_map = json.loads(updated_source.structure_map or "{}")
    phases = runtime_map.get("crawl_plan", {}).get("phases", [])
    assert phases
    assert any(phase["phase_name"] == "artist_directory_letters" for phase in phases)
