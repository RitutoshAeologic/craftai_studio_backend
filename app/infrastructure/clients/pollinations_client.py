import urllib.parse
from app.infrastructure.clients.base import IDiffusionGateway

class PollinationsClient(IDiffusionGateway):
    def __init__(self, base_url: str = "https://image.pollinations.ai/prompt"):
        self.base_url = base_url

    def build_safe_url(self, prompt: str, width: int = 1024, height: int = 1024, seed: int = 42, model: str = "flux") -> str:
        safe_prompt = urllib.parse.quote(prompt.strip(), safe="")
        return (
            f"{self.base_url}/{safe_prompt}"
            f"?width={width}&height={height}&model={model}&seed={seed}&nologo=true&private=true"
        )
