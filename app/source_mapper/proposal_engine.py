from app.source_mapper.types import MappingProposal, PageCluster


BASE_DESTINATIONS: dict[str, list[tuple[str, str, str]]] = {
    "event_detail": [
        ("title", "event", "title"),
        (".event-date", "event", "start_date"),
        (".event-venue", "event", "venue_name"),
    ],
    "artist_detail": [
        ("title", "artist", "title"),
        (".bio", "artist", "bio"),
        (".website", "artist", "website_url"),
    ],
    "exhibition_detail": [
        ("title", "exhibition", "title"),
        (".dates", "exhibition", "start_date"),
    ],
    "venue_detail": [
        ("title", "venue", "title"),
        (".address", "venue", "address"),
    ],
    "artwork_detail": [
        ("title", "artwork", "title"),
        (".medium", "artwork", "medium"),
        (".year", "artwork", "year"),
    ],
    "generic_detail": [
        ("title", "event", "title"),
        ("meta[name='description']", "event", "description"),
    ],
}


def build_proposals(cluster: PageCluster, source_name: str | None = None) -> list[MappingProposal]:
    candidates = BASE_DESTINATIONS.get(cluster.key, BASE_DESTINATIONS["generic_detail"])
    proposals: list[MappingProposal] = []
    for idx, (selector, entity, field) in enumerate(candidates):
        sample_value = source_name if selector == "title" else f"sample_{field}"
        proposals.append(
            MappingProposal(
                selector=selector,
                sample_value=sample_value,
                destination_entity=entity,
                destination_field=field,
                category_target="live-events" if entity == "event" else None,
                confidence_score=max(0.45, round(cluster.confidence_score - (idx * 0.05), 2)),
                rationale=[
                    f"Cluster '{cluster.label}' matched URL pattern",
                    f"Selector '{selector}' is common for {field}",
                ],
            )
        )
    return proposals
