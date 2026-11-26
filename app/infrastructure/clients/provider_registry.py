from typing import Dict, Any, Optional, Tuple
from app.infrastructure.clients.image_provider import (
    ImageProvider,
    ImageProviderRequest,
    ImageProviderResult,
)
from app.infrastructure.clients.fal_image_adapter import FalImageAdapter
from app.infrastructure.clients.openai_image_adapter import OpenAIImageAdapter
from app.infrastructure.clients.gemini_image_adapter import GeminiImageAdapter
from app.services.config_service import ConfigService
from app.core.logging import logger


class ModelUnavailableError(ValueError):
    """Raised when an explicitly requested paid model lacks an active API key."""


class ProviderRegistry:
    """Central registry of direct ImageProvider adapters."""

    def __init__(self):
        self._providers: Dict[str, ImageProvider] = {}

    def register(self, provider_key: str, provider: ImageProvider) -> None:
        self._providers[provider_key.lower()] = provider

    def get(self, provider_key: str) -> Optional[ImageProvider]:
        return self._providers.get(provider_key.lower())


def build_default_provider_registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register("fal", FalImageAdapter())
    registry.register("openai", OpenAIImageAdapter())
    registry.register("google", GeminiImageAdapter())
    return registry


class ModelRouter:
    """
    Config-driven router backed by Supabase `ai_models` + `ai_provider_secrets`.
    Automatically uses paid APIs when keys exist in Supabase, and seamlessly
    routes to local/free fallback models when paid keys are absent.
    """

    def __init__(self, registry: Optional[ProviderRegistry] = None):
        self.registry = registry or build_default_provider_registry()

    def resolve_model(
        self,
        requested_model: Optional[str],
        task: str = "text_to_image",
        quality: str = "standard",
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Returns (resolved_model_config, is_fallback_used).
        If requested paid provider lacks an active API key in Supabase/env,
        walks `fallback_model_key` down to an available local/free engine.
        """
        models = ConfigService.get_ai_models()
        by_key = {m["model_key"]: m for m in models}

        req = (requested_model or "auto").strip().lower()
        alias_map = {
            "flux": "flux_schnell",
            "chatgpt": "gpt_image_1",
            "openai": "gpt_image_1",
            "gemini": "gemini_flash_image",
            "local": "local_sdxl",
            "sdxl": "local_sdxl",
        }

        target_key = alias_map.get(req, req)
        if target_key == "auto" or target_key not in by_key:
            if task == "face_lock_remix":
                target_key = "flux_pulid_facelock"
            elif task == "image_edit":
                target_key = "gemini_flash_image"
            elif quality == "premium":
                target_key = "gpt_image_1"
            else:
                target_key = "flux_schnell"

        chosen = by_key.get(target_key) or by_key.get("local_sdxl") or models[0]
        allow_fallback = req in ("", "auto", "flux", "local", "sdxl")
        if not allow_fallback:
            pk = (chosen.get("provider_key") or "local").lower()
            if pk not in ("local", "cloudflare", "huggingface") and not ConfigService.is_provider_configured(pk):
                raise ModelUnavailableError(
                    f"Model '{chosen['model_key']}' is currently unavailable. Please select 'auto' or a local model."
                )

        is_fallback = False
        visited = set()

        while chosen and chosen["model_key"] not in visited:
            visited.add(chosen["model_key"])
            pk = (chosen.get("provider_key") or "local").lower()
            if ConfigService.is_provider_configured(pk):
                return chosen, is_fallback
            fb_key = chosen.get("fallback_model_key")
            if not fb_key or fb_key not in by_key:
                break
            logger.info(
                f"[ModelRouter] Provider '{pk}' has no active key in Supabase; "
                f"auto-falling back from '{chosen['model_key']}' to '{fb_key}'"
            )
            chosen = by_key[fb_key]
            is_fallback = True

        return chosen, is_fallback

    async def execute(
        self,
        model_cfg: Dict[str, Any],
        task: str,
        prompt: str,
        width: int,
        height: int,
        aspect_ratio: str,
        seed: int,
        negative_prompt: Optional[str] = None,
        reference_image_url: Optional[str] = None,
    ) -> Optional[ImageProviderResult]:
        pk = (model_cfg.get("provider_key") or "local").lower()
        provider = self.registry.get(pk)
        if not provider or not provider.supports(task):
            return None

        api_key = ConfigService.get_provider_key(pk)
        if not api_key:
            return None

        caps = model_cfg.get("capabilities") or {}
        effective_neg = negative_prompt if caps.get("supports_negative_prompt", False) else None

        req = ImageProviderRequest(
            prompt=prompt,
            task=task,
            external_model_id=model_cfg.get("external_model_id", ""),
            width=width,
            height=height,
            aspect_ratio=aspect_ratio,
            seed=seed,
            negative_prompt=effective_neg,
            reference_image_url=reference_image_url,
            capabilities=caps,
            api_key=api_key,
        )

        if task == "face_lock_remix":
            return await provider.facelock_remix(req)
        if task == "image_edit":
            return await provider.edit(req)
        return await provider.generate(req)

