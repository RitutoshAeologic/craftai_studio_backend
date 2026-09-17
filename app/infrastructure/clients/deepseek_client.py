import json
import httpx
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.logging import logger
from app.core.json_parser import clean_and_parse_llm_json
from app.infrastructure.clients.base import ILLMClient, LLMExecutionError

class DeepSeekLLMClient(ILLMClient):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "DEEPSEEK_API_KEY", "")
        self.model = model or getattr(settings, "DEEPSEEK_MODEL", "deepseek-chat")
        self.endpoint = "https://api.deepseek.com/chat/completions"

    async def expand_prompt(self, raw_prompt: str, starter_chip: Optional[str] = None) -> Dict[str, Any]:
        chip_context = f" Preset theme: {starter_chip}." if starter_chip else ""
        system_prompt = (
            "You are an expert generative AI prompt engineer and cinematographic director. "
            "Convert user input into a rich master diffusion prompt. "
            "CRITICAL RULE: If the prompt starts with or contains 'Edit image1 as follows: ', "
            "you MUST preserve 'Edit image1 as follows: ' at the exact start of 'master_prompt' and expand the edit descriptors. "
            "Output valid JSON ONLY with keys: "
            "'master_prompt' (the enhanced prompt), 'negative_prompt' (unwanted artifacts), 'complexity_score' (1-10)."
        )
        user_message = f"Expand this prompt:{chip_context} '{raw_prompt}'"

        if not self.api_key or self.api_key.startswith("your-"):
            raise LLMExecutionError("DeepSeek API key is not configured.")

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
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self.endpoint, headers=headers, json=payload)
                if resp.status_code != 200:
                    raise LLMExecutionError(f"DeepSeek HTTP {resp.status_code}: {resp.text[:120]}")

                data = resp.json()
                raw_content = data["choices"][0]["message"]["content"]
                # clean_and_parse_llm_json automatically strips DeepSeek <think>...</think> reasoning tags
                content = clean_and_parse_llm_json(raw_content)
                if not content or "master_prompt" not in content:
                    raise LLMExecutionError(f"DeepSeek returned invalid JSON: {raw_content[:100]}")

                master = content.get("master_prompt", raw_prompt)
                if raw_prompt.strip().startswith("Edit image1 as follows: ") and not master.strip().startswith("Edit image1 as follows: "):
                    master = f"Edit image1 as follows: {master}"

                return {
                    "master_prompt": master,
                    "negative_prompt": content.get("negative_prompt", "blurry, low quality, distorted, watermark"),
                    "complexity_score": int(content.get("complexity_score", 3)),
                    "model_used": f"deepseek/{self.model}"
                }
        except Exception as e:
            logger.error(f"DeepSeek expand error: {e}")
            raise LLMExecutionError(f"DeepSeek error: {e}")

    async def compile_delta(self, base_prompt: str, user_instruction: str) -> Dict[str, Any]:
        system_prompt = (
            "You are an AI prompt copilot. Merge user instruction into base prompt while preserving locked subjects. "
            "CRITICAL RULE: If base_prompt starts with 'Edit image1 as follows: ', "
            "preserve 'Edit image1 as follows: ' at the exact start of 'compiled_prompt'. "
            "Output valid JSON ONLY with keys: 'compiled_prompt', 'diff', 'suggested_chips'."
        )
        user_message = f"Base prompt: '{base_prompt}'\nChange instruction: '{user_instruction}'"

        if not self.api_key or self.api_key.startswith("your-"):
            raise LLMExecutionError("DeepSeek API key is not configured.")

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
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self.endpoint, headers=headers, json=payload)
                if resp.status_code != 200:
                    raise LLMExecutionError(f"DeepSeek delta HTTP {resp.status_code}: {resp.text[:120]}")

                data = resp.json()
                raw_content = data["choices"][0]["message"]["content"]
                content = clean_and_parse_llm_json(raw_content)
                if not content or "compiled_prompt" not in content:
                    raise LLMExecutionError("DeepSeek delta returned invalid JSON.")

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
                    "model_used": f"deepseek/{self.model}"
                }
        except Exception as e:
            logger.error(f"DeepSeek delta error: {e}")
            raise LLMExecutionError(f"DeepSeek delta error: {e}")
