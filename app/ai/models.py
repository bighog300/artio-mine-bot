from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SiteAnalysisModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    site_type: str = Field(default="unknown")
    cms_platform: str = Field(default="unknown")
    entity_types: list[str] = Field(default_factory=list)
    url_patterns: dict[str, list[str]] = Field(default_factory=dict)
    confidence: int = Field(default=0, ge=0, le=100)
    notes: str | None = None


class SmartMiningConfigModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    crawl_plan: dict[str, Any]
    extraction_rules: dict[str, Any]
    page_type_rules: dict[str, Any] = Field(default_factory=dict)
    record_type_rules: dict[str, Any] = Field(default_factory=dict)
    follow_rules: dict[str, Any] = Field(default_factory=dict)
    asset_rules: dict[str, Any] = Field(default_factory=dict)


class QualityReportModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pages_crawled: int = 0
    records_created: int = 0
    success_rate: float = 0.0
    refined: bool = False
    attempts: int = 1


class SmartMineResultModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    status: Literal["completed", "needs_human_review", "failed"]
    success_rate: float = 0.0
    attempts: int = 0
    analysis: dict[str, Any] = Field(default_factory=dict)
    cost_summary: dict[str, float] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)
    message: str | None = None
