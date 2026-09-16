import io
import os
import uuid
import tempfile
import httpx
from typing import Optional, Union
from PIL import Image
from huggingface_hub import InferenceClient
from gradio_client import Client as GradioClient, handle_file
from app.core.config import settings
from app.core.logging import logger

class HuggingFaceClient:
    """
    Hugging Face Client supporting:
    1. Direct FLUX.1-schnell Text-to-Image via InferenceClient (Zero watermarks, high-fidelity 1024x1024).
    2. Identity-Preserving Image-to-Image via InstantX/InstantID Space (InsightFace landmark lock).
    """
    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.HF_TOKEN
        self.inf_client = InferenceClient(api_key=self.token) if self.token else None
        self._instantid_space: Optional[GradioClient] = None

    def _get_instantid_client(self) -> GradioClient:
        if not self._instantid_space:
            logger.info("[HuggingFace] Connecting to InstantX/InstantID space...")
            self._instantid_space = GradioClient("InstantX/InstantID", hf_token=self.token)
        return self._instantid_space

    async def generate_flux(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        seed: int = 42
    ) -> Optional[bytes]:
        """Generates clean 1024x1024 FLUX.1 image bytes via Hugging Face Inference API."""
        try:
            logger.info(f"[HuggingFace FLUX.1] Generating image for prompt: '{prompt[:100]}...'")
            img = self.inf_client.text_to_image(
                prompt=prompt,
                model="black-forest-labs/FLUX.1-schnell"
            )
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"[HuggingFace FLUX.1] Generation failed: {e}")
            return None

    async def generate_instantid(
        self,
        face_image_url_or_path: str,
        prompt: str,
        negative_prompt: Optional[str] = None,
        style_name: str = "(No style)",
        num_steps: int = 25,
        seed: int = 42
    ) -> Optional[bytes]:
        """
        Locks identity of face in [face_image_url_or_path] and renders in desired style using InstantID.
        """
        temp_input_path = None
        try:
            # 1. Resolve image to a local file
            if face_image_url_or_path.startswith("http://") or face_image_url_or_path.startswith("https://"):
                async with httpx.AsyncClient(timeout=15.0) as http_c:
                    r = await http_c.get(face_image_url_or_path)
                    r.raise_for_status()
                    suffix = ".jpg" if "jpeg" in r.headers.get("content-type", "") else ".png"
                    fd, temp_input_path = tempfile.mkstemp(suffix=suffix)
                    with os.fdopen(fd, "wb") as f:
                        f.write(r.content)
            else:
                temp_input_path = face_image_url_or_path

            logger.info(f"[HuggingFace InstantID] Dispatching prediction with face: {temp_input_path}")
            space_client = self._get_instantid_client()

            neg = negative_prompt or "(lowres, low quality, worst quality:1.2), deformed, bad anatomy, blurry, artifacts"

            # Execute InstantID predict
            res = space_client.predict(
                face_image_path=handle_file(temp_input_path),
                pose_image_path=handle_file(temp_input_path),
                prompt=prompt,
                negative_prompt=neg,
                style_name=style_name,
                num_steps=num_steps,
                identitynet_strength_ratio=0.8,
                adapter_strength_ratio=0.8,
                canny_strength=0.4,
                depth_strength=0.4,
                controlnet_selection=['depth'],
                guidance_scale=5.0,
                seed=seed,
                scheduler='EulerDiscreteScheduler',
                enable_LCM=False,
                enhance_face_region=True,
                api_name='/generate_image'
            )

            # InstantID returns: (generated_image_path, usage_tips)
            if res and isinstance(res, (tuple, list)) and len(res) > 0:
                output_file = res[0]
                if output_file and os.path.exists(output_file):
                    with open(output_file, "rb") as out_f:
                        data = out_f.read()
                    logger.info(f"[HuggingFace InstantID] Generation succeeded! ({len(data)} bytes)")
                    return data

            logger.warning("[HuggingFace InstantID] Prediction completed but no output file found.")
            return None
        except Exception as e:
            logger.error(f"[HuggingFace InstantID] Error during InstantID predict: {e}")
            return None
        finally:
            if temp_input_path and temp_input_path.startswith(tempfile.gettempdir()):
                try:
                    os.remove(temp_input_path)
                except Exception:
                    pass
