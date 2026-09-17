from typing import Dict, Any, List, Optional
from app.infrastructure.clients.base import ILLMClient
from app.infrastructure.clients.gemini_llm_client import GeminiLLMClient
from app.infrastructure.clients.groq_client import GroqClient
from app.infrastructure.clients.deepseek_client import DeepSeekLLMClient
from app.infrastructure.clients.local_llm_client import LocalOfflineLLMClient
from app.infrastructure.clients.openai_client import OpenAILLMClient
from app.infrastructure.clients.claude_client import ClaudeLLMClient
from app.core.config import settings
from app.core.logging import logger

class LLMClientFactory:
    """
    Central factory for instantiating and resolving Multi-LLM client adapters.
    Supports dynamic hot-reloading from Supabase app_settings and environment variables.
    """
    def __init__(self):
        self._clients: Dict[str, ILLMClient] = {}

    def get_client(self, provider_or_model: str, config: Optional[Dict[str, Any]] = None) -> ILLMClient:
        cfg = config or {}
        name = (provider_or_model or "").strip().lower()

        # 1. DeepSeek Official
        if "deepseek" in name:
            model = cfg.get("deepseek_model") or getattr(settings, "DEEPSEEK_MODEL", "deepseek-chat")
            return DeepSeekLLMClient(model=model)

        # 2. Gemini
        if "gemini" in name:
            model = cfg.get("gemini_model") or getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
            if "-" in name and name != "gemini":
                model = provider_or_model
            return GeminiLLMClient(model=model)

        # 3. Groq LPU
        if "groq" in name or "qwen" in name or "llama" in name:
            model = cfg.get("groq_model") or getattr(settings, "GROQ_MODEL", "qwen/qwen3.8-27b")
            if "/" in name or "-" in name and name != "groq":
                model = provider_or_model
            return GroqClient(model=model)

        # 4. OpenAI / ChatGPT
        if "openai" in name or "gpt" in name:
            model = cfg.get("openai_model") or getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
            return OpenAILLMClient(model=model)

        # 5. Anthropic Claude
        if "claude" in name or "anthropic" in name:
            model = cfg.get("claude_model") or getattr(settings, "CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
            return ClaudeLLMClient(model=model)

        # 6. Local Deterministic Offline Engine
        if "local" in name or "offline" in name:
            return LocalOfflineLLMClient()

        # Default provider fallback
        default_provider = cfg.get("provider") or getattr(settings, "DEFAULT_LLM_PROVIDER", "gemini")
        if default_provider != provider_or_model:
            return self.get_client(default_provider, cfg)

        return GeminiLLMClient()

    def get_fallback_chain(self, primary_target: Optional[str], config: Optional[Dict[str, Any]] = None) -> List[ILLMClient]:
        """
        Builds an ordered list of LLM clients to attempt sequentially.
        Ensures zero-downtime prompt compilation across multi-LLM providers.
        """
        cfg = config or {}
        configured_order: List[str] = cfg.get("fallback_order", ["gemini", "groq", "local"])

        order: List[str] = []
        if primary_target and primary_target.strip():
            order.append(primary_target.strip().lower())

        for p in configured_order:
            if p.lower() not in [x.lower() for x in order]:
                order.append(p.lower())

        if "local" not in [x.lower() for x in order]:
            order.append("local")

        clients: List[ILLMClient] = []
        for name in order:
            try:
                client = self.get_client(name, cfg)
                clients.append(client)
            except Exception as e:
                logger.warning(f"Could not build client for {name}: {e}")

        if not clients:
            clients = [LocalOfflineLLMClient()]

        return clients
