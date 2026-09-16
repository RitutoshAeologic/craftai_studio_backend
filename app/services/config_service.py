import time
from typing import Dict, Any
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
            "tier_prices": {"flux": 2.0, "gemini": 3.0, "chatgpt": 3.0}
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
        except Exception:
            # Fall back to defaults if table not yet seeded
            _CONFIG_CACHE = defaults

        return _CONFIG_CACHE

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
