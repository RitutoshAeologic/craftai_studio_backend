import unittest
from fastapi.testclient import TestClient
from app.main import app

class CreativeToolsTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_tools_history_endpoint(self):
        resp = self.client.get("/api/v1/prompt-engineering/tools/history?user_id=00000000-0000-0000-0000-000000000000&limit=10")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), list)

    def test_ai_background_endpoint(self):
        payload = {
            "image_url": "https://images.unsplash.com/photo-1523275335684-37898b6baf30",
            "mode": "pure_white",
            "quality": "1k"
        }
        resp = self.client.post("/api/v1/prompt-engineering/tools/ai-background", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "completed")
        self.assertEqual(data.get("mode"), "pure_white")
        self.assertTrue("output_url" in data)

    def test_ai_expand_endpoint(self):
        payload = {
            "image_url": "https://images.unsplash.com/photo-1523275335684-37898b6baf30",
            "target_ratio": "16:9"
        }
        resp = self.client.post("/api/v1/prompt-engineering/tools/ai-expand", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "completed")
        self.assertEqual(data.get("target_ratio"), "16:9")

    def test_upscale_endpoint(self):
        payload = {
            "image_url": "https://images.unsplash.com/photo-1523275335684-37898b6baf30",
            "scale_factor": 2
        }
        resp = self.client.post("/api/v1/prompt-engineering/tools/upscale", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "completed")

    def test_product_detail_endpoint(self):
        payload = {
            "image_url": "https://images.unsplash.com/photo-1523275335684-37898b6baf30",
            "product_name": "Obsidian Watch"
        }
        resp = self.client.post("/api/v1/prompt-engineering/tools/product-detail", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "completed")

    def test_marketing_poster_endpoint(self):
        payload = {
            "topic": "Summer Sale",
            "category": "Promotion",
            "headline": "UP TO 50% OFF"
        }
        resp = self.client.post("/api/v1/prompt-engineering/tools/marketing-poster", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "completed")

if __name__ == "__main__":
    unittest.main()
