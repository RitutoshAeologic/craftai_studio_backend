import os
import time
import io
import cv2
import numpy as np
import onnxruntime as ort
from PIL import Image
from typing import Tuple, Optional
from huggingface_hub import hf_hub_download
from app.core.logging import logger

class DDColorService:
    """
    Dual-Decoder Colorization (DDColor) ONNX Service.
    Restores natural, high-fidelity color to vintage or B&W photos
    while preserving 100% of native luminance, edge micro-contrast, and texture sharpness.
    """
    _instance: Optional["DDColorService"] = None

    def __init__(self):
        self._session = None
        logger.info("[DDColor] Initializing service...")

    @classmethod
    def get_instance(cls) -> "DDColorService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _ensure_session(self):
        if self._session is None:
            logger.info("[DDColor] Lazy-loading DDColor ONNX model...")
            t0 = time.time()
            model_path = hf_hub_download(
                repo_id="edgetools/ddcolor",
                filename="ddcolor-tiny-fp16.onnx"
            )
            # Use CPU execution provider for broad compatibility and low RAM
            opts = ort.SessionOptions()
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            self._session = ort.InferenceSession(
                model_path,
                sess_options=opts,
                providers=["CPUExecutionProvider"]
            )
            logger.info(f"[DDColor] Loaded ONNX session in {time.time()-t0:.2f}s")

    def colorize(
        self,
        image_bytes: bytes,
        saturation: float = 1.0
    ) -> Tuple[bytes, float]:
        """
        Colorizes image_bytes.
        Returns: (output_png_bytes, elapsed_ms)
        """
        self._ensure_session()
        t0 = time.time()

        # 1. Decode input image
        np_img = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
        if img_bgr is None:
            raise ValueError("Could not decode input image bytes for colorization")

        orig_h, orig_w = img_bgr.shape[:2]

        # 2. Convert to LAB and extract native full-resolution Luminance channel (L)
        img_lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
        orig_l = img_lab[:, :, 0]

        # 3. Downsample L channel to 512x512 for DDColor neural decoder
        l_512 = cv2.resize(orig_l, (512, 512), interpolation=cv2.INTER_AREA)
        l_norm = (l_512.astype(np.float32) / 255.0)
        inp = np.repeat(l_norm[:, :, np.newaxis], 3, axis=2).transpose(2, 0, 1)[np.newaxis, ...]

        # 4. Neural Color Space Inference (predicts AB chromatic channels)
        ab_out = self._session.run(None, {"input": inp})[0]  # [1, 2, 512, 512]
        ab_512 = ab_out[0].transpose(1, 2, 0)  # [512, 512, 2]

        # 5. High-Order Bicubic Upsample AB to match the original native image resolution
        ab_orig = cv2.resize(ab_512, (orig_w, orig_h), interpolation=cv2.INTER_CUBIC)

        # 6. Apply optional saturation tuning
        if saturation != 1.0:
            ab_orig = np.clip(ab_orig * saturation, -128.0, 127.0)

        ab_u8 = np.clip(ab_orig + 128.0, 0, 255).astype(np.uint8)

        # 7. Reconstruct LAB using original full-res L channel -> 100% texture preservation!
        color_lab = np.dstack([orig_l, ab_u8])
        color_bgr = cv2.cvtColor(color_lab, cv2.COLOR_LAB2BGR)

        # 8. Encode to PNG
        success, encoded_buf = cv2.imencode(".png", color_bgr)
        if not success:
            raise RuntimeError("Failed to encode colorized result to PNG")

        elapsed_ms = (time.time() - t0) * 1000
        logger.info(f"[DDColor] Colorized {orig_w}x{orig_h} in {elapsed_ms:.1f}ms (saturation={saturation})")
        return encoded_buf.tobytes(), elapsed_ms
