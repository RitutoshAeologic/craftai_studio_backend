import unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app

class TestCrossPlatformContracts(unittest.TestCase):
    """
    Cross-Platform Automated Contract Test Suite.
    Ensures that changes made by any backend engineer never break
    Flutter Mobile (Dio / Native) or Next.js Web (Axios / Browser) contracts.
    """
    def setUp(self):
        self.client = TestClient(app)

    # ─────────────────────────────────────────────────────────────
    # 1. Health & Routing Parity (Root vs /api/v1 Base URLs)
    # ─────────────────────────────────────────────────────────────
    def test_health_endpoints_parity(self):
        """Guarantees clients with baseUrl /api/v1 or root / never hit 404."""
        res_root = self.client.get("/health")
        self.assertEqual(res_root.status_code, 200)
        self.assertEqual(res_root.json().get("status"), "healthy")

        res_v1 = self.client.get("/api/v1/health")
        self.assertEqual(res_v1.status_code, 200)
        self.assertEqual(res_v1.json().get("status"), "healthy")

    # ─────────────────────────────────────────────────────────────
    # 2. Vision Scanner Contract (Body JSON vs Query Parameter)
    # ─────────────────────────────────────────────────────────────
    @patch("app.services.vision_service.VisionService.scan_photo", new_callable=AsyncMock)
    def test_vision_scan_json_body_photo_url(self, mock_scan):
        mock_scan.return_value = {
            "extracted_prompt": "Vintage 1985 portrait",
            "detected_style": "Vintage Bollywood",
            "lighting_optics": "35mm grain",
            "model_used": "mock_engine"
        }
        # Web / Mobile sending standard POST JSON body with photo_url
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
        # Web / Mobile sending standard POST JSON body with image_url
        res = self.client.post(
            "/api/v1/vision-scan",
            json={"image_url": "https://images.unsplash.com/photo-1544005313-94ddf0286df2"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("extracted_prompt", data)

    @patch("app.services.vision_service.VisionService.scan_photo", new_callable=AsyncMock)
    def test_vision_scan_query_param_fallback(self, mock_scan):
        mock_scan.return_value = {
            "extracted_prompt": "Vintage 1985 portrait",
            "detected_style": "Vintage Bollywood",
            "lighting_optics": "35mm grain",
            "model_used": "mock_engine"
        }
        # Legacy clients sending query parameter
        res = self.client.post(
            "/api/v1/prompt-engineering/vision-scan?photo_url=https://images.unsplash.com/photo-1544005313-94ddf0286df2"
        )
        self.assertEqual(res.status_code, 200)

    def test_vision_scan_empty_payload_fails_cleanly(self):
        res = self.client.post("/api/v1/vision-scan", json={})
        self.assertEqual(res.status_code, 422)

    # ─────────────────────────────────────────────────────────────
    # 3. Tool Preset Contract (Permissive Ingestion & Dual Output)
    # ─────────────────────────────────────────────────────────────
    @patch("app.services.tool_service.ToolService.execute_preset_tool", new_callable=AsyncMock)
    def test_edit_preset_without_image_url(self, mock_tool):
        """Guarantees mobile & web callers omitting image_url NEVER get 422."""
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

    # ─────────────────────────────────────────────────────────────
    # 4. Background Removal Contract (Base64 + Dual Output Key Parity)
    # ─────────────────────────────────────────────────────────────
    @patch("app.services.tool_service.ToolService.remove_background", new_callable=AsyncMock)
    def test_remove_background_dual_output_keys(self, mock_rmbg):
        """Guarantees both Flutter (output_url) and Web (cutout_url) receive their keys."""
        mock_rmbg.return_value = {
            "task_id": "tool_rmbg_123",
            "status": "completed",
            "output_url": "https://storage.supabase.co/cutout.png",
            "cutout_url": "https://storage.supabase.co/cutout.png",
            "tokens_consumed": 0
        }
        # Test Web sending Base64 Data URL
        res = self.client.post(
            "/api/v1/prompt-engineering/tools/remove-background",
            json={"image_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "completed")
        self.assertIn("output_url", data, "Missing output_url for Flutter mobile client")
        self.assertIn("cutout_url", data, "Missing cutout_url for Next.js web client")
        self.assertEqual(data["output_url"], data["cutout_url"])

    # ─────────────────────────────────────────────────────────────
    # 5. Visual Generation Contract (Extended Attributes Tolerant)
    # ─────────────────────────────────────────────────────────────
    @patch("app.services.generation_service.GenerationService.dispatch", new_callable=AsyncMock)
    def test_generation_dispatch_extended_fields(self, mock_dispatch):
        """Guarantees web & mobile can send negative_prompt & structured_metadata without 422."""
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

    # ─────────────────────────────────────────────────────────────
    # 6. Ephemeral Reference Cleanup Contract
    # ─────────────────────────────────────────────────────────────
    def test_cleanup_reference_flexible_keys(self):
        """Accepts image_url, file_path, url, or path without error."""
        res = self.client.post(
            "/api/v1/prompt-engineering/cleanup-reference",
            json={"image_url": "https://storage.example.com/ref.png"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json().get("status"), "purged")

    # ─────────────────────────────────────────────────────────────
    # 7. Browser Preflight CORS Contract (Next.js localhost:3000)
    # ─────────────────────────────────────────────────────────────
    def test_cors_preflight_for_web_browsers(self):
        """Guarantees browser Axios / Fetch from web client gets valid CORS headers."""
        res = self.client.options(
            "/api/v1/prompt-engineering/expand",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization, content-type, ngrok-skip-browser-warning"
            }
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("access-control-allow-origin", res.headers)
        self.assertEqual(res.headers.get("access-control-allow-credentials"), "true")

if __name__ == "__main__":
    unittest.main()
