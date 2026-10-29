from abc import ABC, abstractmethod
from typing import Tuple, Optional

class IInpaintEngine(ABC):
    """
    Abstract Interface for Magic Object Eraser & Zero-Hallucination Inpainting.
    Supports local ONNX (LaMa) or Cloud API engines (Fal.ai, Replicate).
    """
    @abstractmethod
    async def inpaint(self, image_bytes: bytes, mask_bytes: bytes) -> Tuple[bytes, float]:
        """
        Inpaints masked region.
        Returns: (output_png_bytes, elapsed_latency_ms)
        """
        pass

class IColorizeEngine(ABC):
    """
    Abstract Interface for Vintage Photo Colorizer & Neural Restoration.
    Supports local ONNX (DDColor) or Cloud API engines.
    """
    @abstractmethod
    async def colorize(self, image_bytes: bytes, saturation: float = 1.2) -> Tuple[bytes, float]:
        """
        Restores authentic chromaticity.
        Returns: (output_png_bytes, elapsed_latency_ms)
        """
        pass

class IBackgroundRemoverEngine(ABC):
    """
    Abstract Interface for Alpha Cutout & Subject Masking.
    Supports local CPU (rembg U2Net/U2Netp) or Cloud APIs (BiRefNet, RMBG-1.4).
    """
    @abstractmethod
    async def remove_background(self, image_bytes: bytes) -> bytes:
        """
        Extracts foreground subject with alpha channel.
        Returns: transparent_png_bytes
        """
        pass

class IUpscalerEngine(ABC):
    """
    Abstract Interface for 2x/4x Super-Resolution & Clarity Upscaling.
    Supports local ONNX (RealESRGAN), CPU Optical Lanczos, or Cloud Clarity models.
    """
    @abstractmethod
    async def upscale(self, image_bytes: bytes, scale: int = 2, mode: str = "photo") -> Tuple[bytes, str, str]:
        """
        Upscales image.
        Returns: (output_bytes, original_resolution_str, upscaled_resolution_str)
        """
        pass
