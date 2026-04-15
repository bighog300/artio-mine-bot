from dataclasses import dataclass, field


@dataclass(slots=True)
class DiscoveredPage:
    url: str
    title: str | None = None
    html_snippet: str | None = None


@dataclass(slots=True)
class PageCluster:
    key: str
    label: str
    confidence_score: float
    sample_urls: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MappingProposal:
    selector: str
    sample_value: str | None
    destination_entity: str
    destination_field: str
    confidence_score: float
    rationale: list[str]
    category_target: str | None = None
