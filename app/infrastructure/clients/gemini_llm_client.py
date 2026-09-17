import os
import asyncio
from typing import Dict, Any, Optional
import google.generativeai as genai
from app.core.config import settings
from app.core.logging import logger
from app.core.json_parser import clean_and_parse_llm_json
from app.infrastructure.clients.base import ILLMClient, LLMExecutionError

OPTION_A_PREFIX = "Edit image1 as follows: "

class GeminiLLMClient(ILLMClient):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", "")
        self.model_name = model or getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self._model = genai.GenerativeModel(self.model_name)

    def _sync_generate(self, prompt_input: str) -> str:
        """Runs the synchronous Google AI Studio SDK call."""
        try:
            resp = self._model.generate_content(
                prompt_input,
                generation_config={"response_mime_type": "application/json"}
            )
            return resp.text
        except Exception as e:
            if ("429" in str(e) or "quota" in str(e).lower()) and self.model_name != "gemini-flash-latest":
                logger.warning(f"Gemini {self.model_name} rate-limited. Trying gemini-flash-latest...")
                backup_model = genai.GenerativeModel("gemini-flash-latest")
                resp = backup_model.generate_content(
                    prompt_input,
                    generation_config={"response_mime_type": "application/json"}
                )
                self.model_name = "gemini-flash-latest"
                return resp.text
            raise e

    async def _safe_generate(self, prompt_input: str, timeout: float = 4.5) -> str:
        """Executes in threadpool without blocking FastAPI event loop, with strict timeout."""
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._sync_generate, prompt_input),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Gemini {self.model_name} timed out after {timeout}s.")
            raise LLMExecutionError(f"Gemini timed out after {timeout}s")
        except Exception as e:
            raise LLMExecutionError(str(e))

    async def expand_prompt(self, raw_prompt: str, starter_chip: Optional[str] = None) -> Dict[str, Any]:
        chip_context = f" Preset theme: {starter_chip}." if starter_chip else ""
        system_prompt = (
            "You are an expert generative AI visual director. "
            "Decompose user input into structured visual attributes and compile a master diffusion prompt. "
            "CRITICAL RULE: If the prompt starts with or contains 'Edit image1 as follows: ', "
            "you MUST preserve 'Edit image1 as follows: ' at the exact start of 'master_prompt' and expand the edit descriptors. "
            "Output valid JSON ONLY with keys: "
            "'master_prompt', 'negative_prompt', 'complexity_score' (integer 1-10), "
            "'structured_metadata' (object with 'subject', 'environment', 'lighting', 'camera_optics', 'art_style', 'avoid' array, 'preserved_elements' array)."
        )
        user_message = f"Expand this prompt:{chip_context} '{raw_prompt}'"

        if not self.api_key or self.api_key.startswith("your-"):
            raise LLMExecutionError("Gemini API key is not configured.")

        prompt_input = f"{system_prompt}\n\n{user_message}"
        raw_text = await self._safe_generate(prompt_input, timeout=4.5)
        content = clean_and_parse_llm_json(raw_text)
        if not content or "master_prompt" not in content:
            raise LLMExecutionError(f"Gemini returned invalid or empty JSON: {raw_text[:100]}")

        master = content.get("master_prompt", raw_prompt)
        if raw_prompt.strip().startswith(OPTION_A_PREFIX) and not master.strip().startswith(OPTION_A_PREFIX):
            master = f"{OPTION_A_PREFIX}{master}"

        metadata = content.get("structured_metadata", {
            "subject": raw_prompt,
            "environment": starter_chip or "cinematic scene",
            "lighting": "dramatic atmospheric lighting",
            "camera_optics": "35mm lens, f/1.8",
            "art_style": "photorealistic film still",
            "avoid": ["blurry", "distorted", "lowres"],
            "preserved_elements": []
        })

        return {
            "master_prompt": master,
            "negative_prompt": content.get("negative_prompt", "blurry, low quality, distorted, extra limbs, watermark"),
            "complexity_score": int(content.get("complexity_score", 3)),
            "structured_metadata": metadata,
            "model_used": f"google/{self.model_name}"
        }

    async def compile_delta(self, base_prompt: str, user_instruction: str) -> Dict[str, Any]:
        system_prompt = (
            "You are an AI prompt copilot and visual director. The user wants to adjust their active image prompt. "
            "Merge their instruction into the base prompt while strictly preserving locked subjects and facial features. "
            "CRITICAL RULE: If the base_prompt starts with or contains 'Edit image1 as follows: ', "
            "you MUST preserve 'Edit image1 as follows: ' at the exact start of 'compiled_prompt\. "
            "Output valid JSON ONLY with keys: "
            "'compiled_prompt', 'diff' (object with 'added' string array and 'removed' string array), "
            "'suggested_chips' (array of 3 next suggested modification labels), "
            "'structured_metadata' (object with updated 'subject', 'environment', 'lighting', 'camera_optics', 'art_style', 'avoid' array, 'preserved_elements' array)."
        )
        user_message = f"Base prompt: '{base_prompt}'\nChange instruction: '{user_instruction}'"

        if not self.api_key or self.api_key.startswith("your-"):
            raise LLMExecutionError("Gemini API key is not configured.")

        prompt_input = f"{system_prompt}\n\n{user_message}"
        raw_text = await self._safe_generate(prompt_input, timeout=4.5)
        content = clean_and_parse_llm_json(raw_text)
        if not content or "compiled_prompt" not in content:
            raise LLMExecutionError(f"Gemini delta returned invalid JSON: {raw_text[:100]}")

        compiled = content.get("compiled_prompt", f"{base_prompt}, {user_instruction}")
        if base_prompt.strip().startswith(OPTION_A_PREFIX) and not compiled.strip().startswith(OPTION_A_PREFIX):
            compiled = f"{OPTION_A_PREFIX}{compiled}"

        diff_obj = content.get("diff", {})
        metadata = content.get("structured_metadata", {
            "subject": base_prompt,
            "environment": user_instruction,
            "lighting": "cinematic lighting",
            "camera_optics": "35mm lens",
            "art_style": "cinematic",
            "avoid": ["blurry", "distorted"],
            "preserved_elements": []
        })

        return {
            "compiled_prompt": compiled,
            "diff": {
                "added": diff_obj.get("added", [user_instruction]),
                "removed": diff_obj.get("removed", [])
            },
            "suggested_chips": content.get("suggested_chips", ["Add Rim Light", "35mm Grain", "Bokeh Background"]),
            "structured_metadata": metadata,
            "model_used": f"google/{self.model_name}"
        }
