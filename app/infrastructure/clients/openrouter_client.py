import time
import httpx
from typing import Dict, Any, Optional
from app.infrastructure.clients.base import ILLMClient, LLMExecutionError
from app.services.config_service import ConfigService
from app.core.json_parser import clean_and_parse_llm_json
from app.core.logging import logger

# Module-level Circuit Breaker state for OpenRouter resilience
_FAILURE_TIMESTAMPS: list[float] = []
_CIRCUIT_OPEN_UNTIL: float = 0.0
_CIRCUIT_FAILURE_THRESHOLD = 3
_CIRCUIT_WINDOW_SECONDS = 30.0
_CIRCUIT_COOLDOWN_SECONDS = 120.0


class OpenRouterLLMClient(ILLMClient):
    """
    OpenRouter unified text LLM adapter with:
      - Dynamic Supabase key resolution (`ai_provider_secrets`)
      - Strict 2.5s timeout + Circuit Breaker (opens for 120s after 3 failures in 30s)
      - Zero Data Retention (`data_collection: "deny"`) privacy enforcement
    """

    def __init__(self, model: str = "openai/gpt-4o-mini"):
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    @staticmethod
    def is_circuit_open() -> bool:
        return time.time() < _CIRCUIT_OPEN_UNTIL

    @staticmethod
    def _record_failure() -> None:
        global _FAILURE_TIMESTAMPS, _CIRCUIT_OPEN_UNTIL
        now = time.time()
        _FAILURE_TIMESTAMPS = [t for t in _FAILURE_TIMESTAMPS if now - t <= _CIRCUIT_WINDOW_SECONDS]
        _FAILURE_TIMESTAMPS.append(now)
        if len(_FAILURE_TIMESTAMPS) >= _CIRCUIT_FAILURE_THRESHOLD:
            _CIRCUIT_OPEN_UNTIL = now + _CIRCUIT_COOLDOWN_SECONDS
            logger.warning(
                f"[OpenRouter] Circuit breaker OPENED for {int(_CIRCUIT_COOLDOWN_SECONDS)}s "
                f"after {len(_FAILURE_TIMESTAMPS)} failures"
            )

    @staticmethod
    def _record_success() -> None:
        global _FAILURE_TIMESTAMPS, _CIRCUIT_OPEN_UNTIL
        _FAILURE_TIMESTAMPS.clear()
        _CIRCUIT_OPEN_UNTIL = 0.0

    async def _chat(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        if self.is_circuit_open():
            raise LLMExecutionError("OpenRouter circuit breaker is open; skipping to next fallback")

        api_key = ConfigService.get_provider_key("openrouter")
        if not api_key:
            raise LLMExecutionError("OpenRouter API key not configured in Supabase or env")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://craftai.studio",
            "X-Title": "CraftAI Studio",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.4,
            "max_tokens": 500,
            "provider": {"data_collection": "deny"},  # ZDR privacy enforcement
        }
        try:
            async with httpx.AsyncClient(timeout=2.5) as client:
                resp = await client.post(self.base_url, json=payload, headers=headers)
                if resp.status_code != 200:
                    self._record_failure()
                    raise LLMExecutionError(f"OpenRouter HTTP {resp.status_code}: {resp.text[:200]}")
                content = resp.json()["choices"][0]["message"]["content"]
                self._record_success()
                return clean_and_parse_llm_json(content)
        except LLMExecutionError:
            raise
        except Exception as e:
            self._record_failure()
            logger.warning(f"[OpenRouter] Request failed/timed out ({e})")
            raise LLMExecutionError(str(e)) from e

    async def expand_prompt(self, raw_prompt: str, starter_chip: Optional[str] = None) -> Dict[str, Any]:
        sys_prompt = (
            "You are an expert AI image prompt engineer. Expand the user prompt concisely without adding "
            "unwanted logos, text, or extra subjects. Return strict JSON with keys: "
            "master_prompt (string), negative_prompt (string), complexity_score (int 1-100)."
        )
        usr = f"Prompt: {raw_prompt}" + (f"\nStyle chip: {starter_chip}" if starter_chip else "")
        parsed = await self._chat(sys_prompt, usr)
        parsed.setdefault("master_prompt", raw_prompt)
        parsed.setdefault("negative_prompt", "blurry, low quality, distorted, watermark")
        parsed.setdefault("complexity_score", 75)
        return parsed

    async def compile_delta(self, base_prompt: str, user_instruction: str) -> Dict[str, Any]:
        sys_prompt = (
            "Modify the base image prompt according to the user instruction while preserving core subject. "
            "Return strict JSON with keys: compiled_prompt (string), added (list[str]), "
            "removed (list[str]), suggested_chips (list[str]), delta_summary (string)."
        )
        usr = f"Base prompt: {base_prompt}\nInstruction: {user_instruction}"
        parsed = await self._chat(sys_prompt, usr)
        parsed.setdefault("compiled_prompt", f"{base_prompt}, {user_instruction}")
        parsed.setdefault("added", [])
        parsed.setdefault("removed", [])
        parsed.setdefault("suggested_chips", [])
        return parsed
