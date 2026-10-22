from typing import Optional
import urllib.parse
from app.infrastructure.clients.base import IDiffusionGateway
from app.core.config import settings

class PollinationsClient(IDiffusionGateway):
    def __init__(self, base_url: str = "https://image.pollinations.ai/prompt"):
        self.base_url = base_url

    def build_safe_url(self, prompt: str, width: int = 1024, height: int = 1024, seed: int = 42, model: str = "flux", reference_image: Optional[str] = None) -> str:
        safe_prompt = urllib.parse.quote(prompt.strip(), safe="")
        api_key = settings.POLLINATIONS_API_KEY
        key_param = f"&key={api_key}" if api_key else ""
        image_param = f"&image={urllib.parse.quote(reference_image, safe='')}" if reference_image and reference_image.startswith("http") else ""
        return (
            f"{self.base_url}/{safe_prompt}"
            f"?width={width}&height={height}&model={model}&seed={seed}&nologo=true{image_param}{key_param}"
        )
