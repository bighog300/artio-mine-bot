from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.ai.openai_client import OpenAIClient


@pytest.mark.asyncio
async def test_complete_json_tracks_usage() -> None:
    client = OpenAIClient(api_key="test", default_model="gpt-4o")
    mock_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))],
        usage=SimpleNamespace(prompt_tokens=100, completion_tokens=50, total_tokens=150),
    )
    client._client.chat.completions.create = AsyncMock(return_value=mock_response)

    payload = await client.complete_json(system_prompt="sys", user_prompt="user")
    totals = client.get_usage_totals()

    assert payload["ok"] is True
    assert totals["total_tokens"] == 150
    assert totals["estimated_cost_usd"] > 0
