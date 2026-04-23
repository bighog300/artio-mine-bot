from app.ai.templates import TemplateLibrary


def test_template_library_match_and_apply(tmp_path):
    lib = TemplateLibrary(template_dir=tmp_path)
    lib.create_template(
        {
            "id": "gallery_wp",
            "name": "Gallery WP",
            "profile": {
                "site_type": "art_gallery",
                "cms_platform": "wordpress",
                "entity_types": ["artist"],
                "url_pattern_tokens": ["/artists/"],
            },
            "config": {"crawl_plan": {"phases": [{"base_url": "{url}", "url_pattern": "/artists/[a-z]+/?"}]}, "extraction_rules": {"artist": {"exclude_patterns": ["{domain}/admin"]}}},
        }
    )

    match = lib.match_template(
        {
            "site_type": "art_gallery",
            "cms_platform": "wordpress",
            "entity_types": ["artist"],
            "url_patterns": {"artist": ["/artists/jane/"]},
        }
    )

    assert match is not None
    assert match.template_id == "gallery_wp"

    config = lib.apply_template("gallery_wp", "https://example.org")
    assert config["crawl_plan"]["phases"][0]["base_url"] == "https://example.org"
    assert config["extraction_rules"]["artist"]["exclude_patterns"][0] == "example.org/admin"


def test_template_usage_counter(tmp_path):
    lib = TemplateLibrary(template_dir=tmp_path)
    lib.create_template({"id": "t1", "name": "T1", "profile": {}, "config": {}})
    lib.increment_usage("t1")
    tpl = lib.get_template("t1")
    assert tpl is not None
    assert tpl["usage_count"] == 1
