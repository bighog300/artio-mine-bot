from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import OpenAIClient
from app.db.database import AsyncSessionLocal
from app.pipeline.runner import PipelineRunner

# Singletons
_ai_client: OpenAIClient | None = None
_pipeline_runner: PipelineRunner | None = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_ai_client() -> OpenAIClient:
    global _ai_client
    if _ai_client is None:
        _ai_client = OpenAIClient()
    return _ai_client


async def get_pipeline_runner(db: AsyncSession) -> PipelineRunner:
    ai_client = get_ai_client()
    return PipelineRunner(db=db, ai_client=ai_client)
