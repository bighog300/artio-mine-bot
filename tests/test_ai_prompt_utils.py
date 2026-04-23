from app.ai.prompt_utils import smart_html_preview


def test_smart_html_preview_respects_limit_and_keeps_title() -> None:
    html = "<html><head><title>Example Art Site</title><meta name='description' content='desc'></head><body>" + (
        "<h1>Main Heading</h1><p>Paragraph about exhibition and artists.</p>" * 200
    ) + "</body></html>"
    preview = smart_html_preview(html, max_chars=3000)
    assert len(preview) <= 3000
    assert "Example Art Site" in preview
    assert "Paragraph about exhibition" in preview
