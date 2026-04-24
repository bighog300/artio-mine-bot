from __future__ import annotations

import json
from datetime import UTC, datetime
from dataclasses import dataclass
from typing import Any

import structlog
from openai import APIError, APIStatusError, AsyncOpenAI, RateLimitError

from app.config import settings

logger = structlog.get_logger()


MODEL_PRICING_PER_1K: dict[str, dict[str, float]] = {
    "gpt-4o": {"prompt": 0.005, "completion": 0.015},
    "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
}


class OpenAIClientError(RuntimeError):
    pass


@dataclass
class UsageSummary:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class OpenAIClient:
    def __init__(self, api_key: str | None = None, default_model: str | None = None) -> None:
        self._client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)
        self.default_model = default_model or settings.openai_model_config
        self.usage_by_model: dict[str, UsageSummary] = {}
        self.usage_by_operation: dict[str, UsageSummary] = {}
        self.daily_cost_by_operation: dict[str, dict[str, float]] = {}

    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.1,
        max_attempts: int | None = None,
        operation: str = "general",
    ) -> dict[str, Any]:
        selected_model = model or self.default_model
        attempts = max(1, max_attempts or settings.smart_mode_max_retries)
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                response = await self._client.chat.completions.create(
                    model=selected_model,
                    response_format={"type": "json_object"},
                    temperature=temperature,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                content = response.choices[0].message.content
                if not content:
                    raise OpenAIClientError("OpenAI returned an empty response body.")
                payload = json.loads(content)
                self._track_usage(selected_model, response.usage, operation=operation)
                return payload
            except RateLimitError as exc:
                last_error = exc
                wait_seconds = min(settings.smart_mode_retry_base_seconds * (2 ** (attempt - 1)), 16)
                logger.warning(
                    "openai_rate_limit",
                    attempt=attempt,
                    max_attempts=attempts,
                    model=selected_model,
                    wait_seconds=wait_seconds,
                    error=str(exc),
                )
                if attempt < attempts:
                    import asyncio

                    await asyncio.sleep(wait_seconds)
                    continue
            except (APIStatusError, APIError) as exc:
                last_error = exc
                wait_seconds = min(settings.smart_mode_retry_base_seconds * (2 ** (attempt - 1)), 16)
                logger.warning(
                    "openai_api_error",
                    attempt=attempt,
                    max_attempts=attempts,
                    model=selected_model,
                    wait_seconds=wait_seconds,
                    status_code=getattr(exc, "status_code", None),
                    error=str(exc),
                )
                if attempt < attempts:
                    import asyncio

                    await asyncio.sleep(wait_seconds)
                    continue
            except json.JSONDecodeError as exc:
                logger.error("openai_invalid_json", model=selected_model, error=str(exc))
                raise OpenAIClientError("OpenAI returned invalid JSON in JSON mode.") from exc

        raise OpenAIClientError(f"OpenAI call failed after {attempts} attempts: {last_error}")

    def _track_usage(self, model: str, usage: Any, *, operation: str) -> None:
        if usage is None:
            return
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        total_tokens = int(getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or 0)
        summary = self.usage_by_model.setdefault(model, UsageSummary())
        op_summary = self.usage_by_operation.setdefault(operation, UsageSummary())
        summary.prompt_tokens += prompt_tokens
        summary.completion_tokens += completion_tokens
        summary.total_tokens += total_tokens
        op_summary.prompt_tokens += prompt_tokens
        op_summary.completion_tokens += completion_tokens
        op_summary.total_tokens += total_tokens

        pricing = MODEL_PRICING_PER_1K.get(model, MODEL_PRICING_PER_1K["gpt-4o"])
        cost = (prompt_tokens / 1000) * pricing["prompt"] + (completion_tokens / 1000) * pricing["completion"]
        summary.estimated_cost_usd += cost
        op_summary.estimated_cost_usd += cost
        today = datetime.now(UTC).date().isoformat()
        day = self.daily_cost_by_operation.setdefault(today, {})
        day[operation] = round(float(day.get(operation, 0.0)) + cost, 6)

        logger.info(
            "openai_usage",
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            operation=operation,
            estimated_cost_usd=round(summary.estimated_cost_usd, 6),
        )

    def get_usage_totals(self) -> dict[str, float]:
        total_prompt = sum(item.prompt_tokens for item in self.usage_by_model.values())
        total_completion = sum(item.completion_tokens for item in self.usage_by_model.values())
        total_tokens = sum(item.total_tokens for item in self.usage_by_model.values())
        total_cost = sum(item.estimated_cost_usd for item in self.usage_by_model.values())
        return {
            "prompt_tokens": float(total_prompt),
            "completion_tokens": float(total_completion),
            "total_tokens": float(total_tokens),
            "estimated_cost_usd": round(total_cost, 6),
        }

    def get_operation_totals(self) -> dict[str, dict[str, float]]:
        return {
            operation: {
                "prompt_tokens": float(summary.prompt_tokens),
                "completion_tokens": float(summary.completion_tokens),
                "total_tokens": float(summary.total_tokens),
                "estimated_cost_usd": round(summary.estimated_cost_usd, 6),
            }
            for operation, summary in self.usage_by_operation.items()
        }

    def get_daily_cost_report(self) -> dict[str, dict[str, float]]:
        return {date_key: dict(values) for date_key, values in self.daily_cost_by_operation.items()}
