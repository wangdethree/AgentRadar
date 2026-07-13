"""可替换的外部服务适配层。"""

from app.providers.llm import LLMClient, LLMProviderError, LLMResult

__all__ = ["LLMClient", "LLMProviderError", "LLMResult"]
