import json
import os
from typing import Dict, Any, Optional
import google.generativeai as genai
from app.core.config import settings
from app.core.logging import logger
from app.infrastructure.clients.base import ILLMClient

class GeminiLLMClient(ILLMClient):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", "")
        self.model_name = model or "gemini-2.5-flash"
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self._model = genai.GenerativeModel(self.model_name)

    async def expand_prompt(self, raw_prompt: str, starter_chip: Optional[str] = None) -> Dict[str, Any]:
        chip_context = f" Preset theme: {starter_chip}." if starter_chip else ""
        system_prompt = (
            "You are an expert generative AI prompt engineer and cinematographic director. "
            "Convert user input into a rich master diffusion prompt. Output valid JSON ONLY with keys: "
            "'master_prompt' (the enhanced prompt), 'negative_prompt' (unwanted artifacts), 'complexity_score' (1-10)."
        )
        user_message = f"Expand this prompt:{chip_context} '{raw_prompt}'"

        if self.api_key and not self.api_key.startswith("your-"):
            try:
                prompt_input = f"{system_prompt}\n\n{user_message}"
                resp = self._model.generate_content(
                    prompt_input,
                    generation_config={"response_mime_type": "application/json"}
                )
                content = json.loads(resp.text)
                return {
                    "master_prompt": content.get("master_prompt", raw_prompt),
                    "negative_prompt": content.get("negative_prompt", "blurry, low quality, distorted, extra limbs"),
                    "complexity_score": int(content.get("complexity_score", 3)),
                    "model_used": f"google/{self.model_name} (Live AI)"
                }
            except Exception as e:
                logger.error(f"Gemini LLM expansion error: {e}")

        # Fallback
        chip_tag = f"[{starter_chip}] " if starter_chip else ""
        return {
            "master_prompt": f"{chip_tag}{raw_prompt}, 85mm f/1.4 lens, cinematic lighting, 8k resolution",
            "negative_prompt": "blurry, low quality, deformed hands, extra fingers",
            "complexity_score": 3,
            "model_used": f"google/{self.model_name} (Fallback Engine)"
        }

    async def compile_delta(self, base_prompt: str, user_instruction: str) -> Dict[str, Any]:
        system_prompt = (
            "You are an AI prompt copilot. The user wants to adjust their active image prompt. "
            "Merge their instruction into the base prompt while preserving locked subjects. "
            "Output valid JSON ONLY with keys: 'compiled_prompt' (full merged prompt), "
            "'diff' (object with 'added' string array and 'removed' string array), "
            "'suggested_chips' (array of 3 next suggested modification labels)."
        )
        user_message = f"Base prompt: '{base_prompt}'\nChange instruction: '{user_instruction}'"

        if self.api_key and not self.api_key.startswith("your-"):
            try:
                prompt_input = f"{system_prompt}\n\n{user_message}"
                resp = self._model.generate_content(
                    prompt_input,
                    generation_config={"response_mime_type": "application/json"}
                )
                content = json.loads(resp.text)
                diff_obj = content.get("diff", {})
                return {
                    "compiled_prompt": content.get("compiled_prompt", f"{base_prompt}, {user_instruction}"),
                    "diff": {
                        "added": diff_obj.get("added", [user_instruction]),
                        "removed": diff_obj.get("removed", [])
                    },
                    "suggested_chips": content.get("suggested_chips", ["Add Rim Light", "35mm Grain", "Bokeh Background"]),
                    "model_used": f"google/{self.model_name} (Live AI)"
                }
            except Exception as e:
                logger.error(f"Gemini LLM delta error: {e}")

        return {
            "compiled_prompt": f"{base_prompt}, {user_instruction}, 8k",
            "diff": {"added": [user_instruction], "removed": []},
            "suggested_chips": ["Add Volumetric Smoke", "Moody Lighting", "Switch to Anime Style"],
            "model_used": f"google/{self.model_name} (Fallback Engine)"
        }
