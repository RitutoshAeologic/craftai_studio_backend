import asyncio
import io
from PIL import Image, ImageEnhance, ImageFilter
from typing import Tuple, Optional
from app.infrastructure.tools.base import IUpscalerEngine
from app.infrastructure.clients.onnx_upscaler_client import OnnxUpscalerClient
from app.core.config import settings
from app.core.logging import logger

class CompositeUpscalerEngine(IUpscalerEngine):
    """
    Intelligent Cascading Upscaler:
    1. Attempts Local ONNX Real-ESRGAN if GPU hardware accelerator detected.
    2. Seamlessly cascades to high-speed Optical CPU Lanczos with unsharp masking (guaranteeing sub-second delivery).
    """
    def __init__(self, onnx_client: Optional[OnnxUpscalerClient] = None):
        self.onnx_client = onnx_client or OnnxUpscalerClient()

    def _upscale_cpu_sync(self, input_bytes: bytes, scale: int, mode: str) -> Tuple[bytes, str, str]:
        img = Image.open(io.BytesIO(input_bytes)).convert("RGB")
        orig_w, orig_h = img.size
        original_res = f"{orig_w}x{orig_h}"

        scale = 4 if scale == 4 else 2
        mode_lower = (mode or "photo").lower()

        target_w = min(orig_w * scale, 4096)
        target_h = min(orig_h * scale, 4096)

        img = img.resize((target_w, target_h), resample=Image.Resampling.LANCZOS)

        if mode_lower == "portrait":
            img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=125, threshold=2))
            img = ImageEnhance.Color(img).enhance(1.04)
            img = ImageEnhance.Brightness(img).enhance(1.02)
        elif mode_lower == "anime":
            img = img.filter(ImageFilter.EDGE_ENHANCE_MORE)
            img = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=130, threshold=1))
            img = ImageEnhance.Color(img).enhance(1.10)
        elif mode_lower == "fast":
            img = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=100, threshold=3))
        else:
            img = img.filter(ImageFilter.UnsharpMask(radius=2.0, percent=150, threshold=3))
            img = ImageEnhance.Contrast(img).enhance(1.05)

        upscaled_w, upscaled_h = img.size
        upscaled_res = f"{upscaled_w}x{upscaled_h}"

        output_io = io.BytesIO()
        img.save(output_io, format="JPEG", quality=95, optimize=True)
        return output_io.getvalue(), original_res, upscaled_res

    async def upscale(self, image_bytes: bytes, scale: int = 2, mode: str = "photo") -> Tuple[bytes, str, str]:
        # 1. Attempt GPU ONNX if available
        if self.onnx_client.is_gpu:
            try:
                res = await asyncio.to_thread(self.onnx_client.upscale, image_bytes, scale, mode)
                if res:
                    return res
            except Exception as e:
                logger.warning(f"[Upscaler Engine] GPU ONNX failed ({e}), falling back to CPU optical...")

        # 2. Fast CPU optical fallback
        return await asyncio.to_thread(self._upscale_cpu_sync, image_bytes, scale, mode)
