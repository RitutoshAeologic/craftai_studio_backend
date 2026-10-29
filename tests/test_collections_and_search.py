import unittest
from starlette.testclient import TestClient
from app.main import app

class TestCollectionsAndSearchSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_list_collections(self):
        res = self.client.get("/api/v1/collections")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("collections", data)
        self.assertIn("total", data)
        self.assertGreaterEqual(data["total"], 1)

    def test_create_and_delete_collection(self):
        # Create
        create_res = self.client.post("/api/v1/collections", json={
            "name": "SciFi Art Test",
            "description": "Test collection description",
            "is_private": True
        })
        self.assertEqual(create_res.status_code, 201)
        created = create_res.json()
        col_id = created["id"]
        self.assertEqual(created["name"], "SciFi Art Test")

        # Add Item
        add_res = self.client.post(f"/api/v1/collections/{col_id}/items", json={
            "job_id": "test_job_123",
            "image_url": "https://example.com/test.png"
        })
        self.assertEqual(add_res.status_code, 201)

        # Get Items
        items_res = self.client.get(f"/api/v1/collections/{col_id}/items")
        self.assertEqual(items_res.status_code, 200)
        self.assertEqual(items_res.json()["total"], 1)

        # Remove Item
        del_item_res = self.client.delete(f"/api/v1/collections/{col_id}/items/test_job_123")
        self.assertEqual(del_item_res.status_code, 200)

        # Delete Collection
        del_col_res = self.client.delete(f"/api/v1/collections/{col_id}")
        self.assertEqual(del_col_res.status_code, 200)

    def test_universal_search(self):
        res = self.client.post("/api/v1/search", json={
            "query": "cyberpunk",
            "search_type": "text",
            "categories": ["Cyberpunk"]
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("results", data)
        self.assertIn("total", data)
        self.assertGreaterEqual(data["total"], 1)
        self.assertEqual(data["results"][0]["category"], "Cyberpunk")

    def test_similar_creations(self):
        res = self.client.get("/api/v1/explore/similar/exp_1?limit=4")
        self.assertEqual(res.status_code, 200)
        items = res.json()
        self.assertIsInstance(items, list)
        self.assertLessEqual(len(items), 4)

    def test_quick_save_instagram_style(self):
        # 1. Quick save explore item
        save_res = self.client.post("/api/v1/collections/quick-save", json={
            "explore_prompt_id": "exp_quick_1",
            "image_url": "https://example.com/art.png"
        })
        self.assertEqual(save_res.status_code, 200)
        save_data = save_res.json()
        self.assertTrue(save_data["is_saved"])
        self.assertEqual(save_data["status"], "saved")

        # 2. Check status
        status_res = self.client.get("/api/v1/collections/status/exp_quick_1")
        self.assertEqual(status_res.status_code, 200)
        self.assertTrue(status_res.json()["is_saved"])

        # 3. Unsave via quick-save toggle
        unsave_res = self.client.post("/api/v1/collections/quick-save", json={
            "explore_prompt_id": "exp_quick_1",
            "image_url": "https://example.com/art.png"
        })
        self.assertEqual(unsave_res.status_code, 200)
        self.assertFalse(unsave_res.json()["is_saved"])
        self.assertEqual(unsave_res.json()["status"], "unsaved")

    def test_media_static_endpoint(self):
        # Request non-existent media returns 404
        res = self.client.get("/api/v1/media/non_existent_file.png")
        self.assertEqual(res.status_code, 404)

    def test_dispatch_generation_accepts_client_task_id(self):
        res = self.client.post("/api/v1/prompt-engineering/generation/dispatch", json={
            "task_id": "client_custom_task_999",
            "prompt": "futuristic flying vehicle",
            "width": 1024,
            "height": 1024
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["task_id"], "client_custom_task_999")

if __name__ == "__main__":
    unittest.main()
