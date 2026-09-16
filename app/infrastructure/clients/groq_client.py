import json
import httpx
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.logging import logger
from app.infrastructure.clients.base import ILLMClient

class GroqClient(ILLMClient):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "GROQ_API_KEY", "")
        self.model = model or getattr(settings, "LLM_MODEL_NAME", "llama-3.3-70b-versatile")
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"

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
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    "temperature": 0.6,
                    "response_format": {"type": "json_object"}
                }
                async with httpx.AsyncClient(timeout=6.0) as client:
                    resp = await client.post(self.endpoint, headers=headers, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        content = json.loads(data["choices"][0]["message"]["content"])
                        return {
                            "master_prompt": content.get("master_prompt", raw_prompt),
                            "negative_prompt": content.get("negative_prompt", "blurry, low quality, distorted, extra limbs"),
                            "complexity_score": int(content.get("complexity_score", 3)),
                            "model_used": f"groq/{self.model} (Live LPU)"
                        }
                    else:
                        logger.warning(f"Groq expand HTTP {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.error(f"Groq API expansion error: {e}")

        # Enterprise fallback compiler
        chip_tag = f"[{starter_chip}] " if starter_chip else ""
        return {
            "master_prompt": f"{chip_tag}{raw_prompt}, 85mm f/1.4 lens, cinematic Rembrandt lighting, photorealistic textures, 8k resolution, award winning photography",
            "negative_prompt": "blurry, low quality, deformed hands, extra fingers, watermark, oversaturated",
            "complexity_score": 3,
            "model_used": f"groq/{self.model} (Fallback Engine)"
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
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    "temperature": 0.5,
                    "response_format": {"type": "json_object"}
                }
                async with httpx.AsyncClient(timeout=6.0) as client:
                    resp = await client.post(self.endpoint, headers=headers, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        content = json.loads(data["choices"][0]["message"]["content"])
                        return {
                            "compiled_prompt": content.get("compiled_prompt", f"{base_prompt}, {user_instruction}"),
                            "diff": content.get("diff", {"added": [user_instruction], "removed": []}),
                            "suggested_chips": content.get("suggested_chips", ["Add Rim Light", "35mm Grain", "Bokeh Background"]),
                            "model_used": f"groq/{self.model} (Live LPU)"
                        }
                    else:
                        logger.warning(f"Groq delta HTTP {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.error(f"Groq API delta error: {e}")

        # Enterprise fallback compiler
        cleaned_instruction = user_instruction.replace("is me", "").replace("karo", "").replace("add", "").strip()
        compiled = f"{base_prompt}, {cleaned_instruction}, cinematic lighting, photorealistic textures, 8k"
        added_words = [w for w in user_instruction.split() if len(w) > 3]

        return {
            "compiled_prompt": compiled,
            "diff": {
                "added": added_words if added_words else [user_instruction],
                "removed": []
            },
            "suggested_chips": ["Add Volumetric Smoke", "Moody Low-Key Lighting", "Switch to Anime Style"],
            "model_used": f"groq/{self.model} (Fallback Engine)"
        }
