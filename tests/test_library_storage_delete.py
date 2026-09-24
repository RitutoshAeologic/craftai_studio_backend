import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.library_service import LibraryService

class TestLibraryStorageDelete(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.service = LibraryService()

    def test_extract_storage_path(self):
        # 1. Supabase public URL
        url1 = "https://txiuwtrmfvceddqsjvhk.supabase.co/storage/v1/object/public/user_generations/generations/task_12345.png"
        path1 = self.service.extract_storage_path(url1)
        self.assertEqual(path1, "generations/task_12345.png")

        # 2. Supabase URL with query parameters
        url2 = "https://txiuwtrmfvceddqsjvhk.supabase.co/storage/v1/object/user_generations/ai_backgrounds/bg_abc.png?token=xyz"
        path2 = self.service.extract_storage_path(url2)
        self.assertEqual(path2, "ai_backgrounds/bg_abc.png")

        # 3. Known folder direct path
        url3 = "https://example.com/cdn/upscaled_4k/4k_photo.png"
        path3 = self.service.extract_storage_path(url3)
        self.assertEqual(path3, "upscaled_4k/4k_photo.png")

        # 4. None / empty
        self.assertIsNone(self.service.extract_storage_path(None))
        self.assertIsNone(self.service.extract_storage_path(""))

    @patch("app.services.library_service.get_supabase_admin")
    def test_delete_library_item_success(self, mock_get_admin):
        mock_admin = MagicMock()
        mock_get_admin.return_value = mock_admin

        # Mock table select and delete
        mock_jobs_table = MagicMock()
        mock_select = MagicMock()
        mock_or = MagicMock()
        mock_or.execute.return_value = MagicMock(data=[{
            "id": "job_001",
            "job_id": "task_abc",
            "user_id": "00000000-0000-0000-0000-000000000000",
            "preview_url": "https://supabase.co/storage/v1/object/public/user_generations/generations/task_abc.png"
        }])
        mock_select.or_.return_value = mock_or
        mock_jobs_table.select.return_value = mock_select
        mock_jobs_table.delete.return_value = mock_select

        mock_admin.table.return_value = mock_jobs_table
        mock_storage_bucket = MagicMock()
        mock_admin.storage.from_.return_value = mock_storage_bucket

        res = self.client.delete(
            "/api/v1/prompt-engineering/library/task_abc",
            headers={"Authorization": "Bearer mock_token"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("job_id"), "task_abc")

    @patch("app.services.library_service.get_supabase_admin")
    def test_delete_library_item_via_image_url(self, mock_get_admin):
        mock_admin = MagicMock()
        mock_get_admin.return_value = mock_admin
        mock_jobs_table = MagicMock()
        mock_select = MagicMock()
        mock_or = MagicMock()
        mock_or.execute.return_value = MagicMock(data=[])
        mock_select.or_.return_value = mock_or
        mock_jobs_table.select.return_value = mock_select
        mock_jobs_table.delete.return_value = mock_select
        mock_admin.table.return_value = mock_jobs_table

        img_url = "https://supabase.co/storage/v1/object/public/user_generations/product_details/prod_123.png"
        res = self.client.delete(
            f"/api/v1/library/prod_123?image_url={img_url}",
            headers={"Authorization": "Bearer mock_token"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertIn("product_details/prod_123.png", data.get("purged_paths", []))

    @patch("app.services.library_service.get_supabase_admin")
    def test_delete_storage_image_endpoint(self, mock_get_admin):
        mock_admin = MagicMock()
        mock_get_admin.return_value = mock_admin
        mock_storage = MagicMock()
        mock_admin.storage.from_.return_value = mock_storage

        res = self.client.request(
            "DELETE",
            "/api/v1/storage/image",
            json={"image_url": "https://supabase.co/storage/v1/object/user_generations/marketing_posters/poster_99.png"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("purged_path"), "marketing_posters/poster_99.png")

if __name__ == "__main__":
    unittest.main()
