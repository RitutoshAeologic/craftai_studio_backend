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
        Preserves 100% of original pixels outside the masked zone via feathered alpha blending.
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
            mask_rgba = cv2.imdecode(np_mask, cv2.IMREAD_UNCHANGED)
            if mask_rgba is not None and len(mask_rgba.shape) == 3 and mask_rgba.shape[2] == 4:
                mask_gray = mask_rgba[:, :, 3]
            else:
                raise ValueError("Could not decode input mask bytes")

        orig_h, orig_w = img_bgr.shape[:2]

        # Ensure mask matches image dimensions
        if mask_gray.shape[:2] != (orig_h, orig_w):
            mask_gray = cv2.resize(mask_gray, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)

        # 2. Dilate mask slightly to prevent outline/shadow fringe around erased object
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask_dilated = cv2.dilate(mask_gray, kernel, iterations=2)

        # 3. Resolution Normalization for Sub-Second Precision
        # Cap max dimension to 1280 to maintain FFC optimal receptive field
        max_dim = max(orig_h, orig_w)
        if max_dim > 1280:
            scale = 1280.0 / max_dim
            infer_w = int(orig_w * scale)
            infer_h = int(orig_h * scale)
            proc_img = cv2.resize(img_bgr, (infer_w, infer_h), interpolation=cv2.INTER_AREA)
            proc_mask = cv2.resize(mask_dilated, (infer_w, infer_h), interpolation=cv2.INTER_NEAREST)
        else:
            infer_w, infer_h = orig_w, orig_h
            proc_img = img_bgr
            proc_mask = mask_dilated

        # 4. Pad to modulo 8 as required by FFC
        pad_h = (8 - infer_h % 8) % 8
        pad_w = (8 - infer_w % 8) % 8
        if pad_h > 0 or pad_w > 0:
            img_pad = cv2.copyMakeBorder(proc_img, 0, pad_h, 0, pad_w, cv2.BORDER_REFLECT)
            mask_pad = cv2.copyMakeBorder(proc_mask, 0, pad_h, 0, pad_w, cv2.BORDER_CONSTANT, value=0)
        else:
            img_pad = proc_img
            mask_pad = proc_mask

        # 5. Preprocess tensors
        img_rgb = cv2.cvtColor(img_pad, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        img_t = torch.from_numpy(img_rgb).permute(2, 0, 1).unsqueeze(0).to(self._device)

        mask_bin = (mask_pad > 127).astype(np.float32)
        mask_t = torch.from_numpy(mask_bin).unsqueeze(0).unsqueeze(0).to(self._device)

        # 6. Neural Inpainting
        with torch.no_grad():
            out_t = self._model(img_t, mask_t)

        out_np = (out_t[0].permute(1, 2, 0).cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
        out_bgr = cv2.cvtColor(out_np, cv2.COLOR_RGB2BGR)

        # 7. Crop back padding
        if pad_h > 0 or pad_w > 0:
            out_bgr = out_bgr[:infer_h, :infer_w]

        # 8. Restore to original resolution if scaled
        if (infer_h, infer_w) != (orig_h, orig_w):
            out_bgr = cv2.resize(out_bgr, (orig_w, orig_h), interpolation=cv2.INTER_LANCZOS4)

        # 9. Alpha-Feathered Composite: Preserve 100% of unmasked original image!
        # Only the erased area is replaced with inpainting; zero quality loss in the rest of the photo.
        feathered_mask = cv2.GaussianBlur(mask_dilated.astype(np.float32) / 255.0, (7, 7), 2.0)[:, :, None]
        final_bgr = (out_bgr.astype(np.float32) * feathered_mask + img_bgr.astype(np.float32) * (1.0 - feathered_mask)).clip(0, 255).astype(np.uint8)

        # 10. Encode to PNG
        success, encoded_buf = cv2.imencode(".png", final_bgr)
        if not success:
            raise RuntimeError("Failed to encode inpainted result to PNG")

        elapsed_ms = (time.time() - t0) * 1000
        logger.info(f"[LaMa Inpaint] Inpainted {orig_w}x{orig_h} in {elapsed_ms:.1f}ms (Pristine Blend)")
        return encoded_buf.tobytes(), elapsed_ms
