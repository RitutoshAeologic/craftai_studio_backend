import io
import time
import numpy as np
from PIL import Image
from typing import Optional, Tuple
from huggingface_hub import hf_hub_download
import onnxruntime as ort
from app.core.config import settings
from app.core.logging import logger

class OnnxUpscalerClient:
    """
    Local Zero-Cost Neural Super-Resolution using pre-quantized Real-ESRGAN ONNX weights.
    Runs 100% locally on CPU (or GPU if available) with zero external network latency once cached.
    - RealESRGAN_x4plus: Realistic photos, textures, general imagery.
    - RealESRGAN_x4plus_anime_6B: Digital art, 2D illustrations, anime.
    """
    def __init__(self):
        self._photo_session: Optional[ort.InferenceSession] = None
        self._anime_session: Optional[ort.InferenceSession] = None
        available = ort.get_available_providers()
        self.is_gpu = any(p in available for p in ['CUDAExecutionProvider', 'TensorrtExecutionProvider', 'DmlExecutionProvider'])
        self.providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if self.is_gpu else ['CPUExecutionProvider']

    def _get_session(self, mode: str) -> Optional[ort.InferenceSession]:
        mode_lower = (mode or "").lower()
        is_anime = "anime" in mode_lower or "art" in mode_lower

        if is_anime:
            if not self._anime_session:
                try:
                    logger.info("[ONNX Upscaler] Loading RealESRGAN_x4plus_anime_6B ONNX weights...")
                    model_path = hf_hub_download(
                        repo_id="mhmtaufiq/realesrgan-onnx",
                        filename="RealESRGAN_x4plus_anime_6B.onnx",
                        token=settings.HF_TOKEN or None
                    )
                    self._anime_session = ort.InferenceSession(model_path, providers=self.providers)
                    logger.info("[ONNX Upscaler] RealESRGAN Anime ONNX session ready.")
                except Exception as e:
                    logger.error(f"[ONNX Upscaler] Failed to load anime ONNX model: {e}")
                    return None
            return self._anime_session
        else:
            if not self._photo_session:
                try:
                    logger.info("[ONNX Upscaler] Loading RealESRGAN_x4plus ONNX weights...")
                    model_path = hf_hub_download(
                        repo_id="mhmtaufiq/realesrgan-onnx",
                        filename="RealESRGAN_x4plus.onnx",
                        token=settings.HF_TOKEN or None
                    )
                    self._photo_session = ort.InferenceSession(model_path, providers=self.providers)
                    logger.info("[ONNX Upscaler] RealESRGAN Photo ONNX session ready.")
                except Exception as e:
                    logger.error(f"[ONNX Upscaler] Failed to load photo ONNX model: {e}")
                    return None
            return self._photo_session

    def upscale(
        self,
        input_bytes: bytes,
        scale: int = 2,
        mode: str = "photo"
    ) -> Optional[Tuple[bytes, str, str]]:
        """
        Executes Real-ESRGAN super-resolution.
        Returns: (output_bytes, original_resolution_str, upscaled_resolution_str) or None.
        """
        if not self.is_gpu:
            logger.info(f"[ONNX Upscaler] Hardware accelerator (CUDA/DirectML) not detected on host. Bypassing 70s+ CPU neural inference for '{mode}' mode to guarantee zero client HTTP timeouts.")
            return None

        try:
            sess = self._get_session(mode)
            if not sess:
                return None

            img = Image.open(io.BytesIO(input_bytes)).convert("RGB")
            orig_w, orig_h = img.size
            orig_res = f"{orig_w}x{orig_h}"

            # Safety guard: prevent CPU memory overload if input image is extremely large (> 1536px)
            max_dim = 1536
            if max(orig_w, orig_h) > max_dim:
                ratio = max_dim / float(max(orig_w, orig_h))
                work_img = img.resize((int(orig_w * ratio), int(orig_h * ratio)), resample=Image.Resampling.LANCZOS)
            else:
                work_img = img

            # Convert to float32 [1, 3, H, W] normalized to [0, 1]
            arr = np.array(work_img, dtype=np.float32) / 255.0
            arr = np.transpose(arr, (2, 0, 1))
            arr = np.expand_dims(arr, axis=0)

            input_name = sess.get_inputs()[0].name
            t0 = time.time()
            res = sess.run(None, {input_name: arr})
            elapsed = time.time() - t0

            # Extract output tensor [1, 3, 4*H, 4*W]
            out_arr = res[0][0]
            out_arr = np.clip(out_arr * 255.0, 0, 255).astype(np.uint8)
            out_arr = np.transpose(out_arr, (1, 2, 0))
            out_img = Image.fromarray(out_arr)

            target_scale = max(2, min(int(scale or 2), 4))
            target_w = min(orig_w * target_scale, 4096)
            target_h = min(orig_h * target_scale, 4096)

            # If user requested 2x (or scaled dimension differs from native 4x output), resize cleanly with Lanczos
            if out_img.size != (target_w, target_h):
                out_img = out_img.resize((target_w, target_h), resample=Image.Resampling.LANCZOS)

            upscaled_res = f"{target_w}x{target_h}"
            logger.info(f"[ONNX Upscaler] Completed {mode} {scale}X in {elapsed:.2f}s ({orig_res} -> {upscaled_res})")

            buf = io.BytesIO()
            out_img.save(buf, format="PNG", optimize=True)
            return buf.getvalue(), orig_res, upscaled_res

        except Exception as e:
            logger.warning(f"[ONNX Upscaler] Inference error: {e}", exc_info=True)
            return None
