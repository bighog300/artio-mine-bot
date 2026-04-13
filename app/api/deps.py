from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal

if TYPE_CHECKING:
    from app.ai.client import OpenAIClient
    from app.pipeline.runner import PipelineRunner


_ai_client = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_ai_client() -> "OpenAIClient":
    global _ai_client
    if _ai_client is None:
        from app.ai.client import OpenAIClient

        _ai_client = OpenAIClient()
    return _ai_client


async def get_pipeline_runner(db: AsyncSession) -> "PipelineRunner":
    from app.pipeline.runner import PipelineRunner

    ai_client = get_ai_client()
    return PipelineRunner(db=db, ai_client=ai_client)
