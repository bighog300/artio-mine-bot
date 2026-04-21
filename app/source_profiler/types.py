from dataclasses import dataclass, field


@dataclass(slots=True)
class ProfiledPage:
    url: str
    title: str | None = None
    html_snippet: str | None = None
    out_links: list[str] = field(default_factory=list)


@dataclass(slots=True)
class UrlFamilyCluster:
    family_key: str
    family_label: str
    path_pattern: str
    page_type_candidate: str
    confidence: float
    sample_urls: list[str] = field(default_factory=list)
    diagnostics: dict[str, object] = field(default_factory=dict)
