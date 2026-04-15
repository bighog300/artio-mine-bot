import json

from app.extraction.artist_merge import derive_artist_family_key, merge_artist_payload
from app.extraction.artist_related import extract_artist_related_items
from app.extraction.completeness import compute_artist_completeness


def test_derive_artist_family_key():
    assert derive_artist_family_key("https://art.co.za/aliceelahi/") == "art.co.za::aliceelahi"
    assert derive_artist_family_key("https://art.co.za/aliceelahi/about.php") == "art.co.za::aliceelahi"
    assert derive_artist_family_key("https://art.co.za/aliceelahi/exhibitions.php") == "art.co.za::aliceelahi"


def test_merge_prefers_biography_for_long_bio():
    base = merge_artist_payload(
        existing_raw_data=None,
        page_type="artist_profile_hub",
        source_url="https://art.co.za/aliceelahi/",
        extracted_data={"name": "Alice Elahi", "bio": "Short bio", "website_url": "https://alice.example"},
        related_data={},
    )
    merged = merge_artist_payload(
        existing_raw_data=json.dumps(base),
        page_type="artist_biography",
        source_url="https://art.co.za/aliceelahi/about.php",
        extracted_data={"bio": "Long biography with life history details."},
        related_data={},
    )
    payload = merged["artist_payload"]
    assert payload["bio_short"] == "Short bio"
    assert payload["bio_full"] == "Long biography with life history details."
    assert sorted(merged["source_pages"]) == [
        "https://art.co.za/aliceelahi/",
        "https://art.co.za/aliceelahi/about.php",
    ]


def test_extract_structured_repeated_exhibitions_articles_press():
    html = """
    <ul>
      <li><strong>Solo Show</strong>, Gallery One, 2018</li>
      <li><strong>Group Show</strong>, Gallery Two, 2021</li>
    </ul>
    <div>
      <p><a href='/a1'>Article A</a> by Critic, 2020</p>
      <p><a href='/p1'>Press Mention</a> in Art Times, 2019</p>
    </div>
    """
    exhibitions = extract_artist_related_items("artist_exhibitions", html, "https://art.co.za/alice/exhibitions.php")
    articles = extract_artist_related_items("artist_articles", html, "https://art.co.za/alice/articles.php")
    press = extract_artist_related_items("artist_press", html, "https://art.co.za/alice/press.php")

    assert len(exhibitions["exhibitions"]) >= 2
    assert exhibitions["exhibitions"][0]["title"] == "Solo Show"
    assert len(articles["articles"]) >= 1
    assert articles["articles"][0]["source_url"] == "https://art.co.za/alice/articles.php"
    assert len(press["press"]) >= 1
    assert press["press"][0]["source_url"] == "https://art.co.za/alice/press.php"


def test_completeness_score_and_missing_fields():
    score, missing = compute_artist_completeness(
        {
            "artist_name": "Alice",
            "bio_short": "Painter",
            "email": "alice@example.com",
            "image_urls": ["https://img"],
            "articles": [{"title": "A"}],
            "source_pages": ["https://art.co.za/alice/"],
        }
    )
    assert score > 50
    assert "location_or_nationality" in missing
