from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


class CapabilityNotSupportedError(ValueError):
    """Raised when a provider does not support a requested operation."""


@dataclass
class ImageProviderRequest:
    prompt: str
    task: str = "text_to_image"  # text_to_image | image_edit | face_lock_remix
    external_model_id: str = ""
    width: int = 1024
    height: int = 1024
    aspect_ratio: str = "1:1"
    seed: int = 42
    negative_prompt: Optional[str] = None
    reference_image_url: Optional[str] = None
    capabilities: Dict[str, Any] = field(default_factory=dict)
    api_key: Optional[str] = None


@dataclass
class ImageProviderResult:
    image_bytes: bytes
    provider_key: str
    model_key: str
    external_model_id: str
    provider_job_id: Optional[str] = None
    provider_cost_usd: float = 0.0
    latency_ms: int = 0
    is_fallback_used: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class ImageProvider(ABC):
    """Unified interface for all image generation, editing, and face-lock adapters."""

    provider_key: str = "base"

    @abstractmethod
    def supports(self, task: str) -> bool:
        """Return True if this provider supports the given task type."""

    @abstractmethod
    async def generate(self, req: ImageProviderRequest) -> Optional[ImageProviderResult]:
        """Generate an image from text (and optional style anchor)."""

    async def edit(self, req: ImageProviderRequest) -> Optional[ImageProviderResult]:
        """Edit an existing image using natural-language instructions."""
        raise CapabilityNotSupportedError(
            f"Provider '{self.provider_key}' does not support image_edit"
        )

    async def facelock_remix(self, req: ImageProviderRequest) -> Optional[ImageProviderResult]:
        """Generate an identity-preserving portrait remix using a reference selfie."""
        raise CapabilityNotSupportedError(
            f"Provider '{self.provider_key}' does not support face_lock_remix"
        )

