import time
from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.core.supabase_client import get_supabase_admin
from app.core.logging import logger

_CONFIG_CACHE: Dict[str, Any] = {}
_LAST_FETCH = 0.0
_SECRETS_CACHE: Dict[str, str] = {}
_SECRETS_LAST_FETCH = 0.0
_MODELS_CACHE: List[Dict[str, Any]] = []
_MODELS_LAST_FETCH = 0.0
CACHE_DURATION = 60  # Hot-reload TTL: 60 seconds

DEFAULT_AI_MODELS: List[Dict[str, Any]] = [
    {
        "model_key": "local_sdxl",
        "provider_key": "local",
        "external_model_id": "sdxl-lightning-local",
        "display_name": "CraftAI Local Fast Engine",
        "tasks": ["text_to_image", "image_edit"],
        "tier": "economy",
        "credit_cost": 2.0,
        "fallback_model_key": None,
        "capabilities": {
            "supports_facelock": False,
            "supports_negative_prompt": True,
            "supports_transparency": False,
            "is_local": True,
        },
        "is_active": True,
        "sort_order": 1,
    },
    {
        "model_key": "cloudflare_flux",
        "provider_key": "cloudflare",
        "external_model_id": "@cf/black-forest-labs/flux-1-schnell",
        "display_name": "FLUX.1 Schnell (Serverless)",
        "tasks": ["text_to_image"],
        "tier": "economy",
        "credit_cost": 2.0,
        "fallback_model_key": "local_sdxl",
        "capabilities": {
            "supports_facelock": False,
            "supports_negative_prompt": False,
            "supports_transparency": False,
            "is_local": False,
        },
        "is_active": True,
        "sort_order": 2,
    },
    {
        "model_key": "flux_schnell",
        "provider_key": "fal",
        "external_model_id": "fal-ai/flux/schnell",
        "display_name": "FLUX.1 Schnell (fal.ai)",
        "tasks": ["text_to_image"],
        "tier": "economy",
        "credit_cost": 2.0,
        "fallback_model_key": "cloudflare_flux",
        "capabilities": {
            "supports_facelock": False,
            "supports_negative_prompt": False,
            "supports_transparency": False,
            "aspect_ratio_map": {
                "1:1": "square_hd",
                "16:9": "landscape_16_9",
                "9:16": "portrait_16_9",
                "4:5": "portrait_4_3",
            },
        },
        "is_active": True,
        "sort_order": 3,
    },
    {
        "model_key": "flux_pulid_facelock",
        "provider_key": "fal",
        "external_model_id": "fal-ai/flux-pulid",
        "display_name": "FLUX PuLID (Face-Lock Remix)",
        "tasks": ["face_lock_remix", "text_to_image"],
        "tier": "standard",
        "credit_cost": 3.0,
        "fallback_model_key": "local_sdxl",
        "capabilities": {
            "supports_facelock": True,
            "supports_negative_prompt": True,
            "supports_transparency": False,
        },
        "is_active": True,
        "sort_order": 4,
    },
    {
        "model_key": "gemini_flash_image",
        "provider_key": "google",
        "external_model_id": "gemini-2.5-flash-image",
        "display_name": "Gemini 2.5 Flash Image (Edit)",
        "tasks": ["text_to_image", "image_edit"],
        "tier": "editing",
        "credit_cost": 3.0,
        "fallback_model_key": "local_sdxl",
        "capabilities": {
            "supports_facelock": False,
            "supports_negative_prompt": False,
            "supports_transparency": False,
        },
        "is_active": True,
        "sort_order": 5,
    },
    {
        "model_key": "gpt_image_1",
        "provider_key": "openai",
        "external_model_id": "gpt-image-1",
        "display_name": "GPT Image 1 (HD Studio)",
        "tasks": ["text_to_image", "image_edit"],
        "tier": "premium",
        "credit_cost": 4.0,
        "fallback_model_key": "cloudflare_flux",
        "capabilities": {
            "supports_facelock": False,
            "supports_negative_prompt": False,
            "supports_transparency": True,
            "aspect_ratio_map": {
                "1:1": "1024x1024",
                "16:9": "1536x1024",
                "9:16": "1024x1536",
            },
        },
        "is_active": True,
        "sort_order": 6,
    },
]


class ConfigService:
    @staticmethod
    def refresh_cache() -> None:
        global _LAST_FETCH, _SECRETS_LAST_FETCH, _MODELS_LAST_FETCH
        _LAST_FETCH = 0.0
        _SECRETS_LAST_FETCH = 0.0
        _MODELS_LAST_FETCH = 0.0

    @staticmethod
    def get_settings() -> Dict[str, Any]:
        global _CONFIG_CACHE, _LAST_FETCH
        now = time.time()
        if _CONFIG_CACHE and (now - _LAST_FETCH < CACHE_DURATION):
            return _CONFIG_CACHE

        defaults = {
            "signup_credits": 500.0,
            "royalty_config": {"is_enabled": False, "royalty_percentage": 40.0},
            "download_cost": 2.0,
            "tier_prices": {"flux": 2.0, "gemini": 3.0, "chatgpt": 3.0},
        }

        try:
            admin = get_supabase_admin()
            res = admin.table("app_settings").select("*").execute()
            if res.data:
                for row in res.data:
                    key = row.get("key")
                    val = row.get("value")
                    if key:
                        defaults[key] = val
            _CONFIG_CACHE = defaults
            _LAST_FETCH = now
        except Exception as e:
            logger.warning(f"ConfigService failed to fetch from Supabase, using defaults: {e}")
            _CONFIG_CACHE = defaults

        return _CONFIG_CACHE

    @classmethod
    def get_provider_secrets(cls, force_refresh: bool = False) -> Dict[str, str]:
        """
        Loads API keys dynamically from Supabase `ai_provider_secrets` (service_role only)
        with a 60s TTL cache. Falls back to environment variables when Supabase has no key.
        Allows zero-redeploy activation of paid AI providers as soon as keys are added in Supabase.
        """
        global _SECRETS_CACHE, _SECRETS_LAST_FETCH
        now = time.time()
        if not force_refresh and _SECRETS_CACHE and (now - _SECRETS_LAST_FETCH < CACHE_DURATION):
            return _SECRETS_CACHE

        env_defaults: Dict[str, str] = {
            "fal": (getattr(settings, "FAL_API_KEY", "") or "").strip(),
            "openai": (getattr(settings, "OPENAI_API_KEY", "") or "").strip(),
            "google": (getattr(settings, "GEMINI_API_KEY", "") or "").strip(),
            "openrouter": (getattr(settings, "OPENROUTER_API_KEY", "") or "").strip(),
            "cloudflare": (getattr(settings, "CLOUDFLARE_API_TOKEN", "") or "").strip(),
            "huggingface": (getattr(settings, "HF_API_TOKEN", "") or "").strip(),
        }

        try:
            admin = get_supabase_admin()
            res = admin.table("ai_provider_secrets").select("provider_key, api_key").execute()
            if res.data:
                for row in res.data:
                    pk = (row.get("provider_key") or "").strip().lower()
                    key_val = (row.get("api_key") or "").strip()
                    if pk and key_val:
                        env_defaults[pk] = key_val
        except Exception as e:
            logger.debug(f"[ConfigService] ai_provider_secrets read skipped/fallback to env: {e}")

        _SECRETS_CACHE = env_defaults
        _SECRETS_LAST_FETCH = now
        return _SECRETS_CACHE

    @classmethod
    def get_provider_key(cls, provider_key: str) -> Optional[str]:
        secrets = cls.get_provider_secrets()
        val = (secrets.get(provider_key.lower()) or "").strip()
        return val if val else None

    @classmethod
    def is_provider_configured(cls, provider_key: str) -> bool:
        pk = provider_key.lower().strip()
        if pk == "local":
            return True
        if pk == "cloudflare":
            has_token = bool(cls.get_provider_key("cloudflare"))
            has_acct = bool((getattr(settings, "CLOUDFLARE_ACCOUNT_ID", "") or "").strip())
            return has_token and has_acct
        return bool(cls.get_provider_key(pk))

    @classmethod
    def get_ai_models(cls, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Loads the active AI model catalog from Supabase `ai_models` (with 60s TTL)
        and enriches each entry with real-time `is_available` & `active_mode`.
        """
        global _MODELS_CACHE, _MODELS_LAST_FETCH
        now = time.time()
        raw_models: List[Dict[str, Any]] = []

        if not force_refresh and _MODELS_CACHE and (now - _MODELS_LAST_FETCH < CACHE_DURATION):
            raw_models = _MODELS_CACHE
        else:
            try:
                admin = get_supabase_admin()
                res = (
                    admin.table("ai_models")
                    .select("*")
                    .eq("is_active", True)
                    .order("sort_order", desc=False)
                    .execute()
                )
                if res.data:
                    raw_models = res.data
                else:
                    raw_models = DEFAULT_AI_MODELS
            except Exception as e:
                logger.debug(f"[ConfigService] ai_models table read fallback to defaults: {e}")
                raw_models = DEFAULT_AI_MODELS

            _MODELS_CACHE = raw_models
            _MODELS_LAST_FETCH = now

        enriched: List[Dict[str, Any]] = [
            {
                "model_key": "auto",
                "provider_key": "craftai",
                "external_model_id": "auto",
                "display_name": "Auto (Recommended)",
                "tasks": ["text_to_image", "image_edit", "face_lock_remix"],
                "tier": "standard",
                "credit_cost": 2.0,
                "fallback_model_key": "local_sdxl",
                "capabilities": {
                    "supports_facelock": True,
                    "supports_negative_prompt": True,
                    "supports_transparency": False,
                },
                "is_active": True,
                "sort_order": 0,
                "provider_configured": True,
                "active_mode": "auto_router",
                "is_available": True,
            }
        ]
        for m in raw_models:
            item = dict(m)
            pk = (item.get("provider_key") or "local").lower()
            configured = cls.is_provider_configured(pk)
            is_local = pk in ("local", "cloudflare", "huggingface")
            item["provider_configured"] = configured
            item["active_mode"] = "local_engine" if pk == "local" else ("paid_api" if configured else "unavailable")
            # Explicit paid models show is_available=False in UI when key is missing (only 'auto' falls back)
            item["is_available"] = configured or is_local
            enriched.append(item)
        return enriched

    @classmethod
    def get_llm_config(cls) -> Dict[str, Any]:
        settings_map = cls.get_settings()
        has_openrouter = cls.is_provider_configured("openrouter")
        default_cfg = {
            "provider": "openrouter" if has_openrouter else getattr(settings, "DEFAULT_LLM_PROVIDER", "gemini"),
            "fallback_order": (
                ["openrouter", "gemini", "groq", "local"]
                if has_openrouter
                else ["gemini", "groq", "local"]
            ),
            "gemini_model": getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash"),
            "groq_model": getattr(settings, "GROQ_MODEL", "qwen/qwen3.8-27b"),
            "openai_model": getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
            "claude_model": getattr(settings, "CLAUDE_MODEL", "claude-3-5-sonnet-20241022"),
            "openrouter_model": getattr(settings, "OPENROUTER_MODEL", "openai/gpt-4o-mini"),
        }
        db_cfg = settings_map.get("llm_config")
        if isinstance(db_cfg, dict):
            default_cfg.update(db_cfg)
        return default_cfg

    @classmethod
    def is_royalty_enabled(cls) -> bool:
        cfg = cls.get_settings().get("royalty_config", {})
        return bool(cfg.get("is_enabled", False))

    @classmethod
    def get_royalty_percentage(cls) -> float:
        cfg = cls.get_settings().get("royalty_config", {})
        return float(cfg.get("royalty_percentage", 40.0))

    @classmethod
    def get_signup_credits(cls) -> float:
        return float(cls.get_settings().get("signup_credits", 500.0))
