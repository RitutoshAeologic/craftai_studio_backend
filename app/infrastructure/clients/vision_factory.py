from typing import Optional
from app.infrastructure.clients.base import IVisionClient
from app.infrastructure.clients.gemini_client import GeminiVisionClient
from app.infrastructure.clients.openai_vision_client import OpenAIVisionClient
from app.core.config import settings
from app.core.logging import logger

class VisionClientFactory:
    """
    Central Factory resolving Multimodal Vision scanner adapters.
    Allows zero-effort switching between Gemini 2.5 Flash and OpenAI GPT-4o-mini.
    """
    @staticmethod
    def get_vision_client(provider: Optional[str] = None) -> IVisionClient:
        target = (provider or getattr(settings, "VISION_PROVIDER", "gemini")).lower().strip()
        if "openai" in target or "gpt" in target:
            logger.info("[Vision Factory] Using OpenAIVisionClient (GPT-4o-mini)")
            return OpenAIVisionClient()
        return GeminiVisionClient()
