from app.ai.openai_client import OpenAIClient

__all__ = ["SmartMiner", "OpenAIClient"]


def __getattr__(name: str):
    if name == "SmartMiner":
        from app.ai.smart_miner import SmartMiner

        return SmartMiner
    raise AttributeError(name)
