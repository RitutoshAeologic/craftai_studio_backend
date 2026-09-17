import asyncio
import io
import unittest
from PIL import Image
from app.services.tool_service import ToolService
from app.schemas.tools import ToolPresetRequest

class TestEditPresetTool(unittest.TestCase):
    def setUp(self):
        self.service = ToolService(None, None)

    def test_relight_golden_hour_cpu(self):
        img = Image.new("RGB", (100, 100), color=(100, 100, 100))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")

        out_bytes = self.service._process_image_cpu(
            input_bytes=img_bytes.getvalue(),
            action="relight",
            preset="golden_hour",
            lock_subject=True
        )
        self.assertIsNotNone(out_bytes)
        self.assertTrue(len(out_bytes) > 0)
        out_img = Image.open(io.BytesIO(out_bytes))
        self.assertEqual(out_img.size, (100, 100))

    def test_bokeh_blur_cpu(self):
        img = Image.new("RGB", (120, 120), color=(80, 150, 200))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")

        out_bytes = self.service._process_image_cpu(
            input_bytes=img_bytes.getvalue(),
            action="bokeh",
            preset="soft_bokeh",
            lock_subject=True
        )
        self.assertIsNotNone(out_bytes)
        out_img = Image.open(io.BytesIO(out_bytes))
        self.assertEqual(out_img.size, (120, 120))

    def test_upscale_2x_cpu(self):
        img = Image.new("RGB", (64, 64), color=(50, 50, 50))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")

        out_bytes = self.service._process_image_cpu(
            input_bytes=img_bytes.getvalue(),
            action="upscale",
            preset="lossless_4k",
            lock_subject=True
        )
        self.assertIsNotNone(out_bytes)
        out_img = Image.open(io.BytesIO(out_bytes))
        self.assertEqual(out_img.size, (128, 128))

if __name__ == "__main__":
    unittest.main()
