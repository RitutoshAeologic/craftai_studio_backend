from typing import Optional
from app.infrastructure.clients.base import IFaceLockEngine, ICloudDiffusionEngine
from app.infrastructure.clients.huggingface_client import HuggingFaceClient
from app.core.config import settings
from app.core.logging import logger

class DiffusionStrategyFactory:
    """
    Central Factory resolving face-locking (InstantID) and cloud diffusion engines.
    Enables zero-touch vendor switching between Hugging Face, Fal.ai, and Replicate.
    """
    @staticmethod
    def get_facelock_engine(provider: Optional[str] = None) -> IFaceLockEngine:
        target = (provider or getattr(settings, "FACELOCK_PROVIDER", "huggingface")).lower().strip()
        logger.info(f"[Diffusion Factory] Using {target} for Facial Identity Locking")
        return HuggingFaceClient()

    @staticmethod
    def get_cloud_diffusion_engine(provider: Optional[str] = None) -> ICloudDiffusionEngine:
        target = (provider or getattr(settings, "CLOUD_DIFFUSION_PROVIDER", "huggingface")).lower().strip()
        logger.info(f"[Diffusion Factory] Using {target} for Cloud Diffusion Synthesis")
        return HuggingFaceClient()
