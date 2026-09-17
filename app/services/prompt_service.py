from typing import Optional, Dict, Any, List
from app.infrastructure.clients.base import ILLMClient, LLMExecutionError
from app.infrastructure.clients.factory import LLMClientFactory
from app.services.config_service import ConfigService
from app.schemas.prompt import PromptExpandResponse, PromptDeltaResponse, PromptDeltaDiff, LLMConfigResponse
from app.services.tokenizer import calculate_complexity_charge
from app.core.logging import logger

class PromptService:
    def __init__(
        self,
        factory: Optional[LLMClientFactory] = None,
        groq_client: Optional[ILLMClient] = None,
        gemini_client: Optional[ILLMClient] = None
    ):
        self.factory = factory or LLMClientFactory()
        self._legacy_groq = groq_client
        self._legacy_gemini = gemini_client

    async def get_active_config(self) -> LLMConfigResponse:
        """Returns the dynamic LLM configuration from Supabase or Settings."""
        cfg = ConfigService.get_llm_config()
        return LLMConfigResponse(
            active_provider=cfg.get("provider", "gemini"),
            fallback_order=cfg.get("fallback_order", ["gemini", "groq", "local"]),
            available_providers=["gemini", "groq", "openai", "claude", "local"],
            model_mappings={
                "gemini": cfg.get("gemini_model", "gemini-2.5-flash"),
                "groq": cfg.get("groq_model", "qwen/qwen3.8-27b"),
                "openai": cfg.get("openai_model", "gpt-4o-mini"),
                "claude": cfg.get("claude_model", "claude-3-5-sonnet-20241022"),
                "local": "offline-cinematic-engine"
            }
        )

    async def expand_prompt(
        self,
        raw_prompt: str,
        starter_chip: Optional[str] = None,
        aspect_ratio: str = "1:1",
        ai_model: Optional[str] = None
    ) -> PromptExpandResponse:
        llm_cfg = ConfigService.get_llm_config()
        
        # If client explicitly specifies ai_model, honor it; otherwise dynamic config default
        target = ai_model.strip() if (ai_model and ai_model.strip()) else llm_cfg.get("provider", "gemini")

        clients = self.factory.get_fallback_chain(target, llm_cfg)
        last_error = None

        for client in clients:
            try:
                res = await client.expand_prompt(raw_prompt, starter_chip)
                word_count = len(res["master_prompt"].split())
                complexity_score = int(calculate_complexity_charge(
                    model="flux",
                    word_count=word_count,
                    aspect_ratio=aspect_ratio,
                    is_magic_expanded=True
                ))
                return PromptExpandResponse(
                    master_prompt=res["master_prompt"],
                    negative_prompt=res["negative_prompt"],
                    complexity_score=complexity_score,
                    model_used=res["model_used"],
                    structured_metadata=res.get("structured_metadata")
                )
            except Exception as e:
                last_error = e
                logger.warning(f"Provider {client.__class__.__name__} failed during expand_prompt: {e}. Cascading to next provider...")

        logger.error(f"All LLM providers in cascade failed: {last_error}")
        return PromptExpandResponse(
            master_prompt=f"{raw_prompt}, cinematic lighting, photorealistic textures, 8k",
            negative_prompt="blurry, low quality, distorted",
            complexity_score=3,
            model_used="system/emergency-fallback"
        )

    async def compile_delta(
        self,
        base_prompt: str,
        user_instruction: str,
        ai_model: Optional[str] = None
    ) -> PromptDeltaResponse:
        llm_cfg = ConfigService.get_llm_config()
        target = ai_model.strip() if (ai_model and ai_model.strip()) else llm_cfg.get("provider", "gemini")

        clients = self.factory.get_fallback_chain(target, llm_cfg)
        last_error = None

        for client in clients:
            try:
                res = await client.compile_delta(base_prompt, user_instruction)
                diff_data = res.get("diff", {})
                return PromptDeltaResponse(
                    compiled_prompt=res["compiled_prompt"],
                    diff=PromptDeltaDiff(
                        added=diff_data.get("added", []),
                        removed=diff_data.get("removed", [])
                    ),
                    suggested_chips=res.get("suggested_chips", []),
                    model_used=res["model_used"],
                    structured_metadata=res.get("structured_metadata")
                )
            except Exception as e:
                last_error = e
                logger.warning(f"Provider {client.__class__.__name__} failed during compile_delta: {e}. Cascading to next provider...")

        logger.error(f"All LLM providers in cascade failed: {last_error}")
        return PromptDeltaResponse(
            compiled_prompt=f"{base_prompt}, {user_instruction}, 8k",
            diff=PromptDeltaDiff(added=[user_instruction], removed=[]),
            suggested_chips=["Add Rim Light", "Moody Lighting"],
            model_used="system/emergency-fallback"
        )
