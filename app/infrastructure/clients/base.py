from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class LLMExecutionError(Exception):
    """Raised when an LLM provider fails to generate or returns an unparseable response."""
    pass

class ILLMClient(ABC):
    @abstractmethod
    async def expand_prompt(self, raw_prompt: str, starter_chip: Optional[str] = None) -> Dict[str, Any]:
        """Expands raw user prompt into high-fidelity diffusion tokens and negative prompt."""
        pass

    @abstractmethod
    async def compile_delta(self, base_prompt: str, user_instruction: str) -> Dict[str, Any]:
        """Merges a delta instruction into the active base prompt producing diff tags."""
        pass

class IVisionClient(ABC):
    @abstractmethod
    async def scan_photo(self, photo_url_or_path: str) -> Dict[str, Any]:
        """Scans image aesthetics, camera optics, and style metadata."""
        pass

class IDiffusionGateway(ABC):
    @abstractmethod
    def build_safe_url(self, prompt: str, width: int = 1024, height: int = 1024, seed: int = 42, model: str = "flux") -> str:
        """Builds a compliant, privacy-enforced generation URL."""
        pass
