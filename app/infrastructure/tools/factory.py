from typing import Optional
from app.infrastructure.tools.base import (
    IInpaintEngine,
    IColorizeEngine,
    IBackgroundRemoverEngine,
    IUpscalerEngine
)
from app.infrastructure.tools.inpaint_engine import LocalLamaInpaintEngine, FalAiInpaintEngine
from app.infrastructure.tools.colorize_engine import LocalDDColorEngine, CloudColorizeEngine
from app.infrastructure.tools.bg_remover_engine import LocalRembgEngine, FalBiRefNetEngine
from app.infrastructure.tools.upscaler_engine import CompositeUpscalerEngine
from app.core.config import settings
from app.core.logging import logger

class ToolEngineFactory:
    """
    Central Factory for resolving AI Creative Tool adapters.
    Enables instant switching between local ONNX and cloud providers via environment variables.
    """
    @staticmethod
    def get_inpaint_engine(provider: Optional[str] = None) -> IInpaintEngine:
        target = (provider or getattr(settings, "INPAINT_PROVIDER", "local_lama")).lower().strip()
        if "fal" in target:
            logger.info("[Tool Factory] Using FalAiInpaintEngine")
            return FalAiInpaintEngine()
        return LocalLamaInpaintEngine()

    @staticmethod
    def get_colorize_engine(provider: Optional[str] = None) -> IColorizeEngine:
        target = (provider or getattr(settings, "COLORIZE_PROVIDER", "local_ddcolor")).lower().strip()
        if "cloud" in target:
            logger.info("[Tool Factory] Using CloudColorizeEngine")
            return CloudColorizeEngine()
        return LocalDDColorEngine()

    @staticmethod
    def get_bg_remover_engine(provider: Optional[str] = None) -> IBackgroundRemoverEngine:
        target = (provider or getattr(settings, "BG_REMOVER_PROVIDER", "local_rembg")).lower().strip()
        if "fal" in target or "birefnet" in target:
            logger.info("[Tool Factory] Using FalBiRefNetEngine")
            return FalBiRefNetEngine()
        return LocalRembgEngine()

    @staticmethod
    def get_upscaler_engine(provider: Optional[str] = None) -> IUpscalerEngine:
        return CompositeUpscalerEngine()
