import unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app

class TestAPICompatibility(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoints(self):
        # 1. Root /health
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json().get("status"), "healthy")

        # 2. Api v1 /api/v1/health
        res_v1 = self.client.get("/api/v1/health")
        self.assertEqual(res_v1.status_code, 200)
        self.assertEqual(res_v1.json().get("status"), "healthy")

    @patch("app.services.vision_service.VisionService.scan_photo", new_callable=AsyncMock)
    def test_vision_scan_json_body_photo_url(self, mock_scan):
        mock_scan.return_value = {
            "extracted_prompt": "Vintage 1985 portrait",
            "detected_style": "Vintage Bollywood",
            "lighting_optics": "35mm grain",
            "model_used": "mock_engine"
        }
        res = self.client.post(
            "/api/v1/prompt-engineering/vision-scan",
            json={"photo_url": "https://images.unsplash.com/photo-1544005313-94ddf0286df2"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("detected_style"), "Vintage Bollywood")
        self.assertIn("extracted_prompt", data)

    @patch("app.services.vision_service.VisionService.scan_photo", new_callable=AsyncMock)
    def test_vision_scan_json_body_image_url_alias(self, mock_scan):
        mock_scan.return_value = {
            "extracted_prompt": "Vintage 1985 portrait",
            "detected_style": "Vintage Bollywood",
            "lighting_optics": "35mm grain",
            "model_used": "mock_engine"
        }
        res = self.client.post(
            "/api/v1/vision-scan",
            json={"image_url": "https://images.unsplash.com/photo-1544005313-94ddf0286df2"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("extracted_prompt", data)

    @patch("app.services.vision_service.VisionService.scan_photo", new_callable=AsyncMock)
    def test_vision_scan_query_param(self, mock_scan):
        mock_scan.return_value = {
            "extracted_prompt": "Vintage 1985 portrait",
            "detected_style": "Vintage Bollywood",
            "lighting_optics": "35mm grain",
            "model_used": "mock_engine"
        }
        res = self.client.post(
            "/api/v1/prompt-engineering/vision-scan?photo_url=https://images.unsplash.com/photo-1544005313-94ddf0286df2"
        )
        self.assertEqual(res.status_code, 200)

    def test_vision_scan_empty_payload_fails_cleanly(self):
        res = self.client.post("/api/v1/vision-scan", json={})
        self.assertEqual(res.status_code, 422)

    @patch("app.services.tool_service.ToolService.execute_preset_tool", new_callable=AsyncMock)
    def test_edit_preset_without_image_url(self, mock_tool):
        mock_tool.return_value = {
            "task_id": "tool_job123_abc",
            "status": "completed",
            "applied_tool": "relight",
            "subject_masked": True,
            "tokens_consumed": 0,
            "output_url": "https://storage.supabase.co/transformed.png",
            "image_url": "https://storage.supabase.co/transformed.png"
        }
        res = self.client.post(
            "/api/v1/prompt-engineering/tools/edit-preset",
            json={
                "image_id": "job_sample_test",
                "action": "relight",
                "target_preset": "golden_hour",
                "lock_subject": True
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "completed")
        self.assertIn("output_url", data)
        self.assertIn("image_url", data)

    @patch("app.services.generation_service.GenerationService.dispatch", new_callable=AsyncMock)
    def test_generation_dispatch_extended_fields(self, mock_dispatch):
        mock_dispatch.return_value = {
            "task_id": "gen_test123",
            "tier": "Tier 0 (FLUX.1-schnell via Hugging Face)",
            "status": "ready",
            "estimated_seconds": 5,
            "direct_image_url": "https://storage.supabase.co/flux_out.png"
        }
        res = self.client.post(
            "/api/v1/prompt-engineering/generation/dispatch",
            json={
                "prompt": "Cyberpunk samurai warrior in neon rain",
                "negative_prompt": "blurry, low quality, distorted",
                "structured_metadata": {
                    "subject": "Cyberpunk samurai",
                    "lighting": "Neon glow"
                },
                "width": 1024,
                "height": 1024,
                "model": "flux"
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("task_id", data)
        self.assertIn("direct_image_url", data)

    def test_cleanup_reference_flexible_keys(self):
        res = self.client.post(
            "/api/v1/prompt-engineering/cleanup-reference",
            json={"image_url": "https://storage.example.com/ref.png"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json().get("status"), "purged")

if __name__ == "__main__":
    unittest.main()
