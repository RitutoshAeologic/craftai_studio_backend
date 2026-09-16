import json
import httpx
from typing import Dict, Any, Optional
import google.generativeai as genai
from app.core.config import settings
from app.core.logging import logger
from app.infrastructure.clients.base import IVisionClient

class GeminiVisionClient(IVisionClient):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", "")
        self.model_name = model or "gemini-2.5-flash"
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self._model = genai.GenerativeModel(self.model_name)

    async def scan_photo(self, photo_url_or_path: str) -> Dict[str, Any]:
        """Scans image aesthetics, camera optics, and style metadata."""
        if self.api_key and not self.api_key.startswith("your-"):
            try:
                # Fetch image bytes if URL
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(photo_url_or_path)
                    if resp.status_code == 200:
                        image_part = {
                            "mime_type": resp.headers.get("content-type", "image/jpeg").split(";")[0],
                            "data": resp.content
                        }
                        prompt = (
                            "Analyze this reference image aesthetic concept. "
                            "Output JSON ONLY with keys: 'extracted_prompt' (detailed diffusion prompt), "
                            "'detected_style' (e.g. Editorial Portrait), and 'lighting_optics' (lens and lighting)."
                        )
                        result = self._model.generate_content(
                            [prompt, image_part],
                            generation_config={"response_mime_type": "application/json"}
                        )
                        content = json.loads(result.text)
                        return {
                            "extracted_prompt": content.get("extracted_prompt", f"Study of {photo_url_or_path}"),
                            "detected_style": content.get("detected_style", "Editorial Portraiture"),
                            "lighting_optics": content.get("lighting_optics", "Rembrandt key lighting"),
                            "model_used": f"google/{self.model_name} (Live AI)"
                        }
            except Exception as e:
                logger.error(f"Gemini Vision Error in scan_photo: {e}")

        # Enterprise fallback
        return {
            "extracted_prompt": f"Artistic study inspired by reference, fine art portrait, dramatic chiaroscuro lighting, natural textures, 35mm film grain",
            "detected_style": "Editorial Portraiture",
            "lighting_optics": "Key light 45deg, 85mm f/1.4, shallow depth of field",
            "model_used": f"google/{self.model_name} (Fallback Engine)"
        }

    async def extract_facial_identity(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
        """Extracts high-dimensional facial identity descriptors to condition diffusion prompts."""
        if not self.api_key or self.api_key.startswith("your-"):
            return "individual with distinctive facial features, natural skin tone, expressive eyes"

        try:
            image_part = {
                "mime_type": mime_type,
                "data": image_bytes
            }
            prompt = (
                "You are an expert generative AI facial conditioning engine. "
                "Analyze the person in this image and provide a concise physical facial descriptor "
                "to preserve their exact identity, gender, age, skin tone, facial contours, eye shape, "
                "nose, lips, and hair when generating a new portrait in a different era or style. "
                "Output ONLY a single paragraph of descriptive diffusion tokens (under 40 words), comma-separated. "
                "Do NOT include greetings or preamble."
            )
            result = self._model.generate_content([prompt, image_part])
            descriptor = result.text.strip()
            logger.info(f"[Gemini Vision] Extracted facial identity tokens: {descriptor}")
            return descriptor
        except Exception as e:
            logger.error(f"Gemini facial identity extraction failed: {e}")
            return "person with authentic natural facial features, true-to-life skin tone, clear facial structure"
