from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ai.templates import TemplateLibrary


def build_templates() -> list[dict]:
    base = {
        "crawl_plan": {
            "phases": [
                {
                    "phase_name": "detail_pages",
                    "base_url": "{url}",
                    "url_pattern": "/artists/[a-z0-9\\-]+/?",
                    "pagination_type": "follow_links",
                    "num_pages": 20,
                }
            ]
        },
        "extraction_rules": {
            "artist": {
                "identifiers": ["/artists/[^/]+/?$"],
                "exclude_patterns": ["{domain}/wp-admin"],
                "css_selectors": {"title": "h1", "description": ".bio, .artist-bio"},
            }
        },
        "page_type_rules": {},
        "record_type_rules": {},
        "follow_rules": {},
        "asset_rules": {},
    }

    return [
        {"id": "gallery_squarespace_artists", "name": "Gallery Squarespace Artists", "profile": {"site_type": "art_gallery", "cms_platform": "squarespace", "entity_types": ["artist"], "url_pattern_tokens": ["/artists/"]}, "usage_count": 0, "config": base},
        {"id": "gallery_wordpress_artists", "name": "Gallery WordPress Artists", "profile": {"site_type": "art_gallery", "cms_platform": "wordpress", "entity_types": ["artist"], "url_pattern_tokens": ["/artist/"]}, "usage_count": 0, "config": base},
        {"id": "gallery_wordpress_exhibitions", "name": "Gallery WordPress Exhibitions", "profile": {"site_type": "art_gallery", "cms_platform": "wordpress", "entity_types": ["exhibition"], "url_pattern_tokens": ["/exhibitions/"]}, "usage_count": 0, "config": {**base, "crawl_plan": {"phases": [{"phase_name": "exhibitions", "base_url": "{url}", "url_pattern": "/exhibitions/[a-z0-9\\-]+/?", "pagination_type": "follow_links", "num_pages": 20}]}}},
        {"id": "event_calendar_modern", "name": "Event Calendar Modern", "profile": {"site_type": "events_site", "cms_platform": "custom", "entity_types": ["event"], "url_pattern_tokens": ["/events/", "/calendar/"]}, "usage_count": 0, "config": {**base, "extraction_rules": {"event": {"identifiers": ["/events/[^/]+/?$"], "css_selectors": {"title": "h1", "start_date": "time.start", "end_date": "time.end"}}}}},
        {"id": "event_calendar_wordpress", "name": "Event Calendar WordPress", "profile": {"site_type": "events_site", "cms_platform": "wordpress", "entity_types": ["event"], "url_pattern_tokens": ["/event/"]}, "usage_count": 0, "config": {**base, "crawl_plan": {"phases": [{"phase_name": "events", "base_url": "{url}", "url_pattern": "/event/[a-z0-9\\-]+/?", "pagination_type": "follow_links", "num_pages": 30}]}}},
        {"id": "artist_directory_generic", "name": "Artist Directory Generic", "profile": {"site_type": "artist_directory", "cms_platform": "custom", "entity_types": ["artist"], "url_pattern_tokens": ["/directory/", "/artists/"]}, "usage_count": 0, "config": base},
        {"id": "museum_collection", "name": "Museum Collection", "profile": {"site_type": "museum", "cms_platform": "custom", "entity_types": ["artwork", "artist"], "url_pattern_tokens": ["/collection/", "/artworks/"]}, "usage_count": 0, "config": {**base, "extraction_rules": {"artwork": {"identifiers": ["/collection/[^/]+/?$"], "css_selectors": {"title": "h1", "medium": ".medium", "year": ".year"}}}}},
        {"id": "venue_program_wordpress", "name": "Venue Program WordPress", "profile": {"site_type": "venue", "cms_platform": "wordpress", "entity_types": ["event", "venue"], "url_pattern_tokens": ["/program/", "/events/"]}, "usage_count": 0, "config": base},
        {"id": "exhibition_archive_squarespace", "name": "Exhibition Archive Squarespace", "profile": {"site_type": "art_gallery", "cms_platform": "squarespace", "entity_types": ["exhibition"], "url_pattern_tokens": ["/exhibitions/", "/archive/"]}, "usage_count": 0, "config": base},
        {"id": "magazine_artist_profiles", "name": "Magazine Artist Profiles", "profile": {"site_type": "publication", "cms_platform": "custom", "entity_types": ["artist", "article"], "url_pattern_tokens": ["/artists/", "/features/"]}, "usage_count": 0, "config": base},
    ]


def main() -> None:
    library = TemplateLibrary()
    for template in build_templates():
        library.create_template(template)
    print("Created 10 initial templates")


if __name__ == "__main__":
    main()
