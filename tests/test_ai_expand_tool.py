import unittest
import asyncio
import numpy as np
from PIL import Image
import io
from app.schemas.tools import AiExpandRequest, AiExpandResponse
from app.services.tool_service import ToolService

class FakeInpaintEngine:
    async def inpaint(self, image_bytes: bytes, mask_bytes: bytes):
        # Returns image_bytes as inpainted output
        return image_bytes, 12.5

class FakeStorageProvider:
    async def upload(self, data: bytes, folder: str = "media", **kwargs) -> str:
        ext = kwargs.get("ext", "jpg")
        return f"https://mock-storage.supabase.co/{folder}/out.{ext}"

class TestAiExpandTool(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = ToolService(
            inpaint_engine=FakeInpaintEngine(),
            storage_provider=FakeStorageProvider()
        )

    def test_compute_alignment_offsets(self):
        w, h = 100, 100
        new_w, new_h = 200, 200

        # Center
        px, py = self.service._compute_alignment_offsets(w, h, new_w, new_h, "center")
        self.assertEqual(px, 50)
        self.assertEqual(py, 50)

        # Left
        px, py = self.service._compute_alignment_offsets(w, h, new_w, new_h, "left")
        self.assertEqual(px, 0)
        self.assertEqual(py, 50)

        # Right
        px, py = self.service._compute_alignment_offsets(w, h, new_w, new_h, "right")
        self.assertEqual(px, 100)
        self.assertEqual(py, 50)

        # Top
        px, py = self.service._compute_alignment_offsets(w, h, new_w, new_h, "top")
        self.assertEqual(px, 50)
        self.assertEqual(py, 0)

        # Bottom
        px, py = self.service._compute_alignment_offsets(w, h, new_w, new_h, "bottom")
        self.assertEqual(px, 50)
        self.assertEqual(py, 100)

        # Auto with ground contact
        salient_grounded = (10, 20, 90, 95)  # max_y=95 >= 85
        px, py = self.service._compute_alignment_offsets(w, h, new_w, new_h, "auto", salient_grounded)
        self.assertEqual(py, 100)

    async def test_execute_ai_expand_fast_engine(self):
        # Create a small 64x64 test image
        img = Image.new("RGB", (64, 64), color=(120, 180, 220))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        raw_bytes = buf.getvalue()

        req = AiExpandRequest(
            target_ratio="16:9",
            alignment="left",
            engine="fast"
        )

        # Bypass network download by mocking _download_image_bytes
        async def mock_download(url):
            return raw_bytes
        self.service._download_image_bytes = mock_download

        resp = await self.service.execute_ai_expand(req)
        self.assertIsInstance(resp, AiExpandResponse)
        self.assertEqual(resp.status, "completed")
        self.assertEqual(resp.target_ratio, "16:9")
        self.assertEqual(resp.alignment, "left")
        self.assertEqual(resp.engine, "fast")
        self.assertTrue(resp.output_url.startswith("https://") or resp.output_url.startswith("data:"))

if __name__ == "__main__":
    unittest.main()
