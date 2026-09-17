import json
import httpx
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.logging import logger
from app.core.json_parser import clean_and_parse_llm_json
from app.infrastructure.clients.base import ILLMClient, LLMExecutionError

class ClaudeLLMClient(ILLMClient):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "ANTHROPIC_API_KEY", "")
        self.model = model or getattr(settings, "CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
        self.endpoint = "https://api.anthropic.com/v1/messages"

    async def expand_prompt(self, raw_prompt: str, starter_chip: Optional[str] = None) -> Dict[str, Any]:
        chip_context = f" Preset theme: {starter_chip}." if starter_chip else ""
        system_prompt = (
            "You are an expert generative AI prompt engineer and cinematographic director. "
            "Convert user input into a rich master diffusion prompt. "
            "CRITICAL RULE: If the prompt starts with or contains 'Edit image1 as follows: ', "
            "you MUST preserve 'Edit image1 as follows: ' at the exact start of 'master_prompt'. "
            "Output valid JSON ONLY with keys: 'master_prompt', 'negative_prompt', 'complexity_score', 'structured_metadata' (object with 'subject', 'environment', 'lighting', 'camera_optics', 'art_style', 'avoid' array, 'preserved_elements' array)."
        )
        user_message = f"Expand this prompt:{chip_context} '{raw_prompt}'"

        if not self.api_key or self.api_key.startswith("your-"):
            raise LLMExecutionError("Anthropic API key is not configured.")

        try:
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            payload = {
                "model": self.model,
                "max_tokens": 1024,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}]
            }
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(self.endpoint, headers=headers, json=payload)
                if resp.status_code != 200:
                    raise LLMExecutionError(f"Claude expand HTTP {resp.status_code}: {resp.text[:120]}")

                data = resp.json()
                raw_text = data["content"][0]["text"]
                content = clean_and_parse_llm_json(raw_text)
                if not content or "master_prompt" not in content:
                    raise LLMExecutionError("Claude returned invalid JSON structure.")

                master = content.get("master_prompt", raw_prompt)
                if raw_prompt.strip().startswith("Edit image1 as follows: ") and not master.strip().startswith("Edit image1 as follows: "):
                    master = f"Edit image1 as follows: {master}"

                return {
                    "master_prompt": master,
                    "negative_prompt": content.get("negative_prompt", "blurry, low quality, distorted"),
                    "complexity_score": int(content.get("complexity_score", 3)),
                    "structured_metadata": content.get("structured_metadata", {"subject": raw_prompt, "environment": starter_chip or "scene", "lighting": "cinematic", "camera_optics": "35mm", "art_style": "photorealistic", "avoid": ["blurry"], "preserved_elements": []}),
                    "structured_metadata": content.get("structured_metadata", {"subject": base_prompt, "environment": user_instruction, "lighting": "cinematic", "camera_optics": "35mm", "art_style": "cinematic", "avoid": ["blurry"], "preserved_elements": []}),
                    "model_used": f"anthropic/{self.model}"
                }
        except Exception as e:
            logger.error(f"Claude expand error: {e}")
            raise LLMExecutionError(f"Claude error: {e}")

    async def compile_delta(self, base_prompt: str, user_instruction: str) -> Dict[str, Any]:
        system_prompt = (
            "You are an AI prompt copilot. Merge instruction into the base prompt while preserving locked subjects. "
            "CRITICAL RULE: If base_prompt starts with 'Edit image1 as follows: ', "
            "preserve 'Edit image1 as follows: ' at the start of 'compiled_prompt'. "
            "Output valid JSON ONLY with keys: 'compiled_prompt', 'diff', 'suggested_chips', 'structured_metadata'."
        )
        user_message = f"Base prompt: '{base_prompt}'\nChange instruction: '{user_instruction}'"

        if not self.api_key or self.api_key.startswith("your-"):
            raise LLMExecutionError("Anthropic API key is not configured.")

        try:
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            payload = {
                "model": self.model,
                "max_tokens": 1024,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}]
            }
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(self.endpoint, headers=headers, json=payload)
                if resp.status_code != 200:
                    raise LLMExecutionError(f"Claude delta HTTP {resp.status_code}: {resp.text[:120]}")

                data = resp.json()
                raw_text = data["content"][0]["text"]
                content = clean_and_parse_llm_json(raw_text)
                if not content or "compiled_prompt" not in content:
                    raise LLMExecutionError("Claude delta returned invalid JSON structure.")

                compiled = content.get("compiled_prompt", f"{base_prompt}, {user_instruction}")
                if base_prompt.strip().startswith("Edit image1 as follows: ") and not compiled.strip().startswith("Edit image1 as follows: "):
                    compiled = f"Edit image1 as follows: {compiled}"

                diff_obj = content.get("diff", {})
                return {
                    "compiled_prompt": compiled,
                    "diff": {
                        "added": diff_obj.get("added", [user_instruction]),
                        "removed": diff_obj.get("removed", [])
                    },
                    "suggested_chips": content.get("suggested_chips", ["Add Rim Light", "35mm Grain", "Bokeh Background"]),
                    "structured_metadata": content.get("structured_metadata", {"subject": raw_prompt, "environment": starter_chip or "scene", "lighting": "cinematic", "camera_optics": "35mm", "art_style": "photorealistic", "avoid": ["blurry"], "preserved_elements": []}),
                    "structured_metadata": content.get("structured_metadata", {"subject": base_prompt, "environment": user_instruction, "lighting": "cinematic", "camera_optics": "35mm", "art_style": "cinematic", "avoid": ["blurry"], "preserved_elements": []}),
                    "model_used": f"anthropic/{self.model}"
                }
        except Exception as e:
            logger.error(f"Claude delta error: {e}")
            raise LLMExecutionError(f"Claude delta error: {e}")
