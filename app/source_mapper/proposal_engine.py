from app.source_mapper.types import MappingProposal, PageCluster


SCHEMA_BLUEPRINTS: dict[str, list[tuple[str, str, str]]] = {
    "detail_event": [
        ("h1", "event", "title"),
        ("time, .date", "event", "start_date"),
        (".description, article p", "event", "description"),
    ],
    "detail_profile": [
        ("h1", "artist", "title"),
        (".bio, .about, article p", "artist", "bio"),
        ("a[href^='http']", "artist", "website_url"),
    ],
    "detail_content": [
        ("h1", "organization", "title"),
        ("article p, .content p", "organization", "description"),
        ("a[href^='http']", "organization", "website_url"),
    ],
    "listing_page": [
        ("main a[href]", "event", "url"),
        ("main h2, main h3", "event", "title"),
    ],
    "directory_index": [
        ("a[href]", "organization", "url"),
        ("a[href]", "organization", "title"),
    ],
    "section_landing": [
        ("h1", "organization", "title"),
        ("p", "organization", "description"),
    ],
    "root_page": [
        ("title", "organization", "title"),
        ("meta[name='description']", "organization", "description"),
    ],
    "detail_page": [
        ("h1", "organization", "title"),
        ("article p, .content", "organization", "description"),
    ],
    "generic_page": [
        ("title", "organization", "title"),
        ("meta[name='description']", "organization", "description"),
    ],
}



def build_proposals(cluster: PageCluster, source_name: str | None = None) -> list[MappingProposal]:
    candidates = SCHEMA_BLUEPRINTS.get(cluster.key, SCHEMA_BLUEPRINTS["generic_page"])
    proposals: list[MappingProposal] = []
    for idx, (selector, entity, field) in enumerate(candidates):
        sample_value = source_name if selector == "title" else f"sample_{field}"
        proposals.append(
            MappingProposal(
                selector=selector,
                sample_value=sample_value,
                destination_entity=entity,
                destination_field=field,
                category_target=None,
                confidence_score=max(0.45, round(cluster.confidence_score - (idx * 0.05), 2)),
                rationale=[
                    f"Cluster '{cluster.label}' mapped to schema blueprint '{cluster.key}'",
                    f"Selector '{selector}' commonly captures '{field}'",
                ],
            )
        )
    return proposals
