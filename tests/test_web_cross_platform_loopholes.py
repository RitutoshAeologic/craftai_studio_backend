import unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app

class TestWebCrossPlatformLoopholes(unittest.TestCase):
    """
    Exhaustive regression test suite ensuring zero loopholes between
    FastAPI backend and Next.js Web (Axios / TypeScript / camelCase)
    as well as Flutter Mobile (Dio / Dart / snake_case).
    """
    def setUp(self):
        self.client = TestClient(app)
        self.dummy_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    # ─────────────────────────────────────────────────────────────
    # 1. CamelCase Ingestion Parity (Next.js / TypeScript Web Payloads)
    # ─────────────────────────────────────────────────────────────
    def test_ai_background_accepts_camelcase(self):
        """Web sending imageUrl, customBackdrop, aspectRatio never gets 422."""
        res = self.client.post(
            "/api/v1/prompt-engineering/tools/ai-background",
            json={
                "imageUrl": self.dummy_b64,
                "mode": "pure_white",
                "customBackdrop": "Minimalist white studio",
                "aspectRatio": "1:1",
                "userId": "00000000-0000-0000-0000-000000000000"
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "completed")
        # Dual-output key verification
        self.assertIn("output_url", data)
        self.assertIn("image_url", data)
        self.assertIn("url", data)
        self.assertEqual(data["output_url"], data["image_url"])
        self.assertEqual(data["output_url"], data["url"])

    def test_ai_expand_accepts_camelcase(self):
        """Web sending imageUrl and targetRatio never gets 422."""
        res = self.client.post(
            "/api/v1/prompt-engineering/tools/ai-expand",
            json={
                "imageUrl": self.dummy_b64,
                "targetRatio": "16:9",
                "userId": "00000000-0000-0000-0000-000000000000"
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "completed")
        self.assertIn("output_url", data)
        self.assertIn("image_url", data)
        self.assertEqual(data["output_url"], data["image_url"])

    def test_upscale_accepts_camelcase(self):
        """Web sending imageUrl and scaleFactor never gets 422."""
        res = self.client.post(
            "/api/v1/prompt-engineering/tools/upscale",
            json={
                "imageUrl": self.dummy_b64,
                "scaleFactor": 4,
                "userId": "00000000-0000-0000-0000-000000000000"
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "completed")
        self.assertIn("output_url", data)
        self.assertIn("image_url", data)
        self.assertEqual(data.get("credits_deducted"), 2.0)

    def test_product_detail_accepts_camelcase(self):
        """Web sending imageUrl, productName, aspectRatio never gets 422."""
        res = self.client.post(
            "/api/v1/prompt-engineering/tools/product-detail",
            json={
                "imageUrl": self.dummy_b64,
                "productName": "Wireless Noise Canceling Headphones",
                "aspectRatio": "4:5",
                "userId": "00000000-0000-0000-0000-000000000000"
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "completed")
        self.assertIn("output_url", data)
        self.assertIn("image_url", data)
        self.assertEqual(data.get("credits_deducted"), 10.0)

    def test_marketing_poster_accepts_camelcase(self):
        """Web sending topic, aspectRatio, userId never gets 422."""
        res = self.client.post(
            "/api/v1/prompt-engineering/tools/marketing-poster",
            json={
                "topic": "Cyber Week Sale",
                "category": "Flash Sale",
                "aspectRatio": "9:16",
                "headline": "UP TO 70% OFF",
                "userId": "00000000-0000-0000-0000-000000000000"
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "completed")
        self.assertIn("output_url", data)
        self.assertIn("image_url", data)
        self.assertIn("url", data)

    # ─────────────────────────────────────────────────────────────
    # 2. Browser CORS Preflight Contract on Tools
    # ─────────────────────────────────────────────────────────────
    def test_cors_preflight_on_tools(self):
        """Ensures browser Axios / Fetch from Next.js gets valid CORS headers on tools."""
        res = self.client.options(
            "/api/v1/prompt-engineering/tools/ai-background",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization, content-type"
            }
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("access-control-allow-origin", res.headers)
        self.assertEqual(res.headers.get("access-control-allow-credentials"), "true")

    # ─────────────────────────────────────────────────────────────
    # 3. History Boundary Cases (Pre-Auth / Undefined userId)
    # ─────────────────────────────────────────────────────────────
    def test_history_handles_undefined_user_id(self):
        """Web passing 'undefined' or 'null' when auth is loading returns empty list cleanly."""
        res_undef = self.client.get("/api/v1/prompt-engineering/tools/history?user_id=undefined")
        self.assertEqual(res_undef.status_code, 200)
        self.assertEqual(res_undef.json(), [])

        res_null = self.client.get("/api/v1/prompt-engineering/tools/history?user_id=null")
        self.assertEqual(res_null.status_code, 200)
        self.assertEqual(res_null.json(), [])

if __name__ == "__main__":
    unittest.main()
