import os
import time
import io
import cv2
import numpy as np
import torch
from PIL import Image
from typing import Tuple, Optional
from huggingface_hub import hf_hub_download
from app.core.logging import logger

class LamaInpaintService:
    """
    State-of-the-art Fast Fourier Convolution (FFC) inpainting service (LaMa).
    Sub-second, zero-hallucination texture completion for Object Erasure.
    """
    _instance: Optional["LamaInpaintService"] = None

    def __init__(self):
        self._model = None
        self._device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        logger.info(f"[LaMa Inpaint] Initializing service on device: {self._device}")

    @classmethod
    def get_instance(cls) -> "LamaInpaintService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _ensure_model(self):
        if self._model is None:
            logger.info("[LaMa Inpaint] Lazy-loading TorchScript LaMa model...")
            t0 = time.time()
            model_path = hf_hub_download(
                repo_id="JosephCatrambone/big-lama-torchscript",
                filename="lama.pt"
            )
            self._model = torch.jit.load(model_path, map_location=self._device)
            self._model.eval()
            logger.info(f"[LaMa Inpaint] Loaded model in {time.time()-t0:.2f}s on {self._device}")

    def inpaint(
        self,
        image_bytes: bytes,
        mask_bytes: bytes
    ) -> Tuple[bytes, float]:
        """
        Inpaints image_bytes with mask_bytes (white=remove, black=preserve).
        Returns: (output_png_bytes, elapsed_ms)
        """
        self._ensure_model()
        t0 = time.time()

        # 1. Decode image and mask
        np_img = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
        if img_bgr is None:
            raise ValueError("Could not decode input image bytes")

        np_mask = np.frombuffer(mask_bytes, np.uint8)
        mask_gray = cv2.imdecode(np_mask, cv2.IMREAD_GRAYSCALE)
        if mask_gray is None:
            raise ValueError("Could not decode input mask bytes")

        orig_h, orig_w = img_bgr.shape[:2]

        # Ensure mask matches image dimensions
        if mask_gray.shape[:2] != (orig_h, orig_w):
            mask_gray = cv2.resize(mask_gray, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)

        # 2. Pad to modulo 8 as required by FFC
        pad_h = (8 - orig_h % 8) % 8
        pad_w = (8 - orig_w % 8) % 8
        if pad_h > 0 or pad_w > 0:
            img_pad = cv2.copyMakeBorder(img_bgr, 0, pad_h, 0, pad_w, cv2.BORDER_REFLECT)
            mask_pad = cv2.copyMakeBorder(mask_gray, 0, pad_h, 0, pad_w, cv2.BORDER_CONSTANT, value=0)
        else:
            img_pad = img_bgr
            mask_pad = mask_gray

        # 3. Preprocess tensors
        img_rgb = cv2.cvtColor(img_pad, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        img_t = torch.from_numpy(img_rgb).permute(2, 0, 1).unsqueeze(0).to(self._device)

        mask_bin = (mask_pad > 127).astype(np.float32)
        mask_t = torch.from_numpy(mask_bin).unsqueeze(0).unsqueeze(0).to(self._device)

        # 4. Neural Inpainting
        with torch.no_grad():
            out_t = self._model(img_t, mask_t)

        out_np = (out_t[0].permute(1, 2, 0).cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
        out_bgr = cv2.cvtColor(out_np, cv2.COLOR_RGB2BGR)

        # 5. Crop back to exact original dimensions
        if pad_h > 0 or pad_w > 0:
            out_bgr = out_bgr[:orig_h, :orig_w]

        # 6. Encode to PNG
        success, encoded_buf = cv2.imencode(".png", out_bgr)
        if not success:
            raise RuntimeError("Failed to encode inpainted result to PNG")

        elapsed_ms = (time.time() - t0) * 1000
        logger.info(f"[LaMa Inpaint] Inpainted {orig_w}x{orig_h} in {elapsed_ms:.1f}ms")
        return encoded_buf.tobytes(), elapsed_ms
