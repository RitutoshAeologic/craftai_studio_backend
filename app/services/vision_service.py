from app.infrastructure.clients.base import IVisionClient
from app.schemas.vision import VisionScanResponse

class VisionService:
    def __init__(self, vision_client: IVisionClient):
        self.vision_client = vision_client

    async def scan_photo(self, photo_url_or_path: str) -> VisionScanResponse:
        res = await self.vision_client.scan_photo(photo_url_or_path)
        return VisionScanResponse(
            extracted_prompt=res["extracted_prompt"],
            detected_style=res["detected_style"],
            lighting_optics=res["lighting_optics"],
            model_used=res["model_used"]
        )
