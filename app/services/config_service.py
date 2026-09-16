import time
from typing import Dict, Any, List
from app.core.config import settings
from app.core.supabase_client import get_supabase_admin
from app.core.logging import logger

_CONFIG_CACHE: Dict[str, Any] = {}
_LAST_FETCH = 0
CACHE_DURATION = 60  # Cache for 60 seconds

class ConfigService:
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
            "llm_config": {
                "provider": getattr(settings, "DEFAULT_LLM_PROVIDER", "gemini"),
                "fallback_order": ["gemini", "groq", "local"],
                "gemini_model": getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash"),
                "groq_model": getattr(settings, "GROQ_MODEL", "qwen/qwen3.8-27b"),
                "openai_model": getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
                "claude_model": getattr(settings, "CLAUDE_MODEL", "claude-3-5-sonnet-20241022"),
            }
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
    def get_llm_config(cls) -> Dict[str, Any]:
        settings_map = cls.get_settings()
        default_cfg = {
            "provider": getattr(settings, "DEFAULT_LLM_PROVIDER", "gemini"),
            "fallback_order": ["gemini", "groq", "local"],
            "gemini_model": getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash"),
            "groq_model": getattr(settings, "GROQ_MODEL", "qwen/qwen3.8-27b"),
            "openai_model": getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
            "claude_model": getattr(settings, "CLAUDE_MODEL", "claude-3-5-sonnet-20241022"),
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
