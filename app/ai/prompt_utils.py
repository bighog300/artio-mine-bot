from __future__ import annotations

from bs4 import BeautifulSoup


def compact_prompt(text: str, *, max_chars: int) -> str:
    return " ".join(text.split())[:max_chars]


def smart_html_preview(html: str, *, max_chars: int = 3000) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    title = (soup.title.text.strip() if soup.title and soup.title.text else "")[:140]
    meta_desc = ""
    meta = soup.select_one("meta[name=description]")
    if meta and meta.get("content"):
        meta_desc = str(meta.get("content")).strip()[:220]

    important_chunks: list[str] = []
    for node in soup.select("h1, h2, h3, nav a, article p, main p, p, li"):
        text = " ".join(node.get_text(" ", strip=True).split())
        if len(text) < 20:
            continue
        important_chunks.append(text)
        if sum(len(part) for part in important_chunks) > int(max_chars * 0.85):
            break

    prefix = f"TITLE: {title}\nMETA: {meta_desc}\n"
    body = "\n".join(important_chunks)
    combined = f"{prefix}{body}".strip()
    if len(combined) <= max_chars:
        return combined
    head = combined[: int(max_chars * 0.7)]
    tail = combined[-int(max_chars * 0.3) :]
    return f"{head}\n...\n{tail}"[:max_chars]
