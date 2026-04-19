from app.db.models import SourceMappingRow, SourceMappingSample


def build_preview(
    rows: list[SourceMappingRow],
    sample: SourceMappingSample,
    *,
    low_confidence_threshold: float,
) -> tuple[list[dict], dict, dict, list[str], str | None, dict]:
    extractions: list[dict] = []
    record_preview: dict[str, str] = {}
    category_preview: dict[str, list[str]] = {}
    warnings: list[str] = []
    field_sources: dict[str, list[str]] = {}

    for row in rows:
        if row.status == "rejected" or not row.is_enabled:
            continue
        normalized = (row.sample_value or "").strip() or None
        warning = None
        if normalized is None:
            warning = "Empty sample value"
        elif float(row.confidence_score or 0.0) < low_confidence_threshold:
            warning = "Low confidence mapping - moderation required"
            warnings.append(f"Low confidence extraction for {row.destination_entity}.{row.destination_field}")

        extractions.append(
            {
                "mapping_row_id": row.id,
                "source_selector": row.selector,
                "raw_value": row.sample_value,
                "normalized_value": normalized,
                "destination_entity": row.destination_entity,
                "destination_field": row.destination_field,
                "category_target": row.category_target,
                "confidence_score": row.confidence_score,
                "warning": warning,
            }
        )
        if normalized is not None:
            record_preview[row.destination_field] = normalized
            field_sources.setdefault(row.destination_field, [])
            if row.selector not in field_sources[row.destination_field]:
                field_sources[row.destination_field].append(row.selector)
        if row.category_target:
            category_preview.setdefault(row.destination_entity, [])
            if row.category_target not in category_preview[row.destination_entity]:
                category_preview[row.destination_entity].append(row.category_target)

    source_snippet = sample.html_snapshot[:400] if sample.html_snapshot else (sample.title[:400] if sample.title else None)
    extended = {
        "page_family": {
            "hub_url": sample.url,
            "child_pages": [sample.url],
        },
        "field_sources": field_sources,
        "linked_images": record_preview.get("linked_images", []),
        "discarded_images": record_preview.get("discarded_images", []),
    }
    return extractions, record_preview, category_preview, warnings, source_snippet, extended
