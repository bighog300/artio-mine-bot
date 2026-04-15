from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RuntimeMetrics:
    pages_processed: int = 0
    pages_expanded: int = 0
    pages_deepened: int = 0
    records_created: int = 0
    records_enriched: int = 0
    duplicate_items_skipped: int = 0
    completeness_total: float = 0.0
    completeness_samples: int = 0

    @property
    def average_completeness(self) -> float:
        if self.completeness_samples == 0:
            return 0.0
        return round(self.completeness_total / self.completeness_samples, 2)


_METRICS = RuntimeMetrics()


def increment(field: str, amount: int = 1) -> None:
    current = getattr(_METRICS, field)
    setattr(_METRICS, field, current + amount)


def observe_completeness(score: float) -> None:
    _METRICS.completeness_total += score
    _METRICS.completeness_samples += 1


def snapshot() -> dict[str, float | int]:
    return {
        "pages_processed": _METRICS.pages_processed,
        "pages_expanded": _METRICS.pages_expanded,
        "pages_deepened": _METRICS.pages_deepened,
        "records_created": _METRICS.records_created,
        "records_enriched": _METRICS.records_enriched,
        "duplicate_items_skipped": _METRICS.duplicate_items_skipped,
        "average_completeness": _METRICS.average_completeness,
    }


def reset() -> None:
    global _METRICS
    _METRICS = RuntimeMetrics()
