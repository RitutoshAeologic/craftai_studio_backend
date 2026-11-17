import unittest
import io
import base64
import numpy as np
import cv2
from PIL import Image
from app.services.tool_service import ToolService
from app.schemas.tools import (
    RemoveBackgroundRequest,
    RemoveObjectRequest,
    UpscaleRequest,
    AiBackgroundRequest,
    ProductDetailRequest,
    )
from app.core.exceptions import ValidationException

class FakeStorageProvider:
    async def upload(self, data: bytes, folder: str = "media", **kwargs) -> str:
        ext = kwargs.get("ext", "png")
        return f"https://mock-storage.supabase.co/{folder}/out.{ext}"

class TestAiToolsEdgeCases(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = ToolService(
            storage_provider=FakeStorageProvider()
        )

    def _create_solid_image_b64(self, color=(255, 255, 255), size=(256, 256)):
        img = Image.new("RGB", size, color=color)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")

    def _create_image_with_subject_b64(self, size=(256, 256)):
        # White background with distinct blue object in the center
        img = np.ones((size[1], size[0], 3), dtype=np.uint8) * 255
        cv2.circle(img, (size[0] // 2, size[1] // 2), 50, (255, 0, 0), -1)
        _, buf = cv2.imencode(".png", img)
        return "data:image/png;base64," + base64.b64encode(buf.tobytes()).decode("utf-8")

    async def test_remove_background_no_subject_fails_cleanly(self):
        """Solid uniform background image should raise ValidationException because no foreground subject exists."""
        solid_b64 = self._create_solid_image_b64(color=(240, 240, 240))
        req = RemoveBackgroundRequest(image_url=solid_b64)
        with self.assertRaises(ValidationException) as ctx:
            await self.service.remove_background(req)
        self.assertIn("No distinct foreground subject found", str(ctx.exception))

    async def test_remove_background_missing_image_fails_cleanly(self):
        req = RemoveBackgroundRequest()
        with self.assertRaises(ValidationException) as ctx:
            await self.service.remove_background(req)
        self.assertIn("Please upload or provide an image", str(ctx.exception))

    async def test_remove_object_missing_mask_fails_cleanly(self):
        solid_b64 = self._create_solid_image_b64()
        req = RemoveObjectRequest(image_url=solid_b64)
        with self.assertRaises(ValidationException) as ctx:
            await self.service.remove_object(req)
        self.assertIn("No object area was selected", str(ctx.exception))

    async def test_remove_object_empty_black_mask_fails_cleanly(self):
        solid_b64 = self._create_solid_image_b64()
        black_mask_b64 = self._create_solid_image_b64(color=(0, 0, 0))
        req = RemoveObjectRequest(image_url=solid_b64, mask_base64=black_mask_b64)
        with self.assertRaises(ValidationException) as ctx:
            await self.service.remove_object(req)
        self.assertIn("No object area was selected", str(ctx.exception))

    async def test_remove_object_oversized_mask_fails_cleanly(self):
        solid_b64 = self._create_solid_image_b64()
        white_mask_b64 = self._create_solid_image_b64(color=(255, 255, 255))
        req = RemoveObjectRequest(image_url=solid_b64, mask_base64=white_mask_b64)
        with self.assertRaises(ValidationException) as ctx:
            await self.service.remove_object(req)
        self.assertIn("Selected area is too large", str(ctx.exception))

    async def test_upscale_missing_image_fails_cleanly(self):
        req = UpscaleRequest()
        with self.assertRaises(ValidationException) as ctx:
            await self.service.upscale_image(req)
        self.assertIn("Please provide a valid image to upscale", str(ctx.exception))

    async def test_ai_background_no_subject_fails_cleanly(self):
        solid_b64 = self._create_solid_image_b64(color=(200, 200, 200))
        req = AiBackgroundRequest(image_url=solid_b64, mode="pure_white")
        with self.assertRaises(ValidationException) as ctx:
            await self.service.execute_ai_background(req)
        self.assertTrue(
            "No distinct foreground subject found" in str(ctx.exception) or
            "No background detected" in str(ctx.exception)
        )

    async def test_product_detail_no_product_fails_cleanly(self):
        solid_b64 = self._create_solid_image_b64(color=(200, 200, 200))
        req = ProductDetailRequest(image_url=solid_b64, product_name="Sneakers")
        with self.assertRaises(ValidationException) as ctx:
            await self.service.execute_product_detail(req)
        self.assertTrue(
            "No distinct product" in str(ctx.exception) or
            "No distinct foreground subject" in str(ctx.exception) or
            "No background detected" in str(ctx.exception)
        )

    async def test_colorize_solid_white_fails_cleanly(self):
        """Solid uniform white image has no textures/shadows to colorize."""
        solid_b64 = self._create_solid_image_b64(color=(255, 255, 255))
        from app.schemas.tools import ColorizeRequest
        req = ColorizeRequest(image_url=solid_b64)
        with self.assertRaises(ValidationException) as ctx:
            await self.service.colorize_image(req)
        self.assertIn("completely blank or uniform", str(ctx.exception))

    async def test_upscale_solid_white_fails_cleanly(self):
        """Solid uniform white image should not waste credits on upscaling."""
        solid_b64 = self._create_solid_image_b64(color=(255, 255, 255))
        req = UpscaleRequest(image_url=solid_b64)
        with self.assertRaises(ValidationException) as ctx:
            await self.service.upscale_image(req)
        self.assertIn("completely blank or uniform", str(ctx.exception))

    async def test_upscale_corrupt_image_fails_cleanly(self):
        corrupt_b64 = "data:image/png;base64,bm90X2FuX2ltYWdlX2F0X2FsbA=="
        req = UpscaleRequest(image_url=corrupt_b64)
        with self.assertRaises(ValidationException) as ctx:
            await self.service.upscale_image(req)
        self.assertIn("corrupted or not a valid image", str(ctx.exception))

if __name__ == "__main__":
    unittest.main()
