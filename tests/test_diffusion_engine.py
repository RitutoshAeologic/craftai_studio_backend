import unittest
from unittest.mock import patch, AsyncMock, MagicMock
from app.infrastructure.clients.sidecar_client import SidecarDiffusionClient
from app.infrastructure.clients.local_sdxl_client import LocalSDXLClient
from app.infrastructure.clients.diffusion_engine import CompositeDiffusionEngine

class TestDiffusionEngineSuite(unittest.IsolatedAsyncioTestCase):
    def test_local_sdxl_availability(self):
        client = LocalSDXLClient()
        self.assertTrue(client.is_available(), "LocalSDXLClient should report available when torch & diffusers installed")
        self.assertIn(client._determine_device(), ["mps", "cpu", "cuda"])

    async def test_sidecar_offline_graceful(self):
        client = SidecarDiffusionClient(base_url="http://127.0.0.1:9999")
        alive = await client.is_alive()
        self.assertFalse(alive, "Unreachable sidecar should report False without crashing")
        res = await client.generate_image("test prompt")
        self.assertIsNone(res)

    @patch("httpx.AsyncClient.get")
    async def test_sidecar_online_detection(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "ready"}
        mock_get.return_value = mock_resp

        client = SidecarDiffusionClient(base_url="http://127.0.0.1:8001")
        alive = await client.is_alive()
        self.assertTrue(alive)

    @patch("httpx.AsyncClient.post")
    async def test_sidecar_generate_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"fake_png_bytes"
        mock_post.return_value = mock_resp

        client = SidecarDiffusionClient(base_url="http://127.0.0.1:8001")
        res = await client.generate_image("photorealistic cyber samurai", width=1024, height=1024)
        self.assertEqual(res, b"fake_png_bytes")

    async def test_composite_engine_prefers_sidecar_when_alive(self):
        mock_sidecar = AsyncMock(spec=SidecarDiffusionClient)
        mock_sidecar.is_alive.return_value = True
        mock_sidecar.generate_image.return_value = b"sidecar_image_bytes"

        mock_local = AsyncMock(spec=LocalSDXLClient)
        mock_hf = AsyncMock()

        engine = CompositeDiffusionEngine(
            sidecar_client=mock_sidecar,
            local_sdxl=mock_local,
            hf_client=mock_hf
        )

        img_bytes = await engine.generate_image("masterpiece prompt")
        self.assertEqual(img_bytes, b"sidecar_image_bytes")
        mock_sidecar.generate_image.assert_awaited_once()
        mock_local.generate_image.assert_not_awaited()

    async def test_composite_engine_cascades_to_local_when_sidecar_down(self):
        mock_sidecar = AsyncMock(spec=SidecarDiffusionClient)
        mock_sidecar.is_alive.return_value = False

        mock_local = AsyncMock(spec=LocalSDXLClient)
        mock_local.is_available.return_value = True
        mock_local.generate_image.return_value = b"local_mps_bytes"

        mock_hf = AsyncMock()

        engine = CompositeDiffusionEngine(
            sidecar_client=mock_sidecar,
            local_sdxl=mock_local,
            hf_client=mock_hf
        )

        img_bytes = await engine.generate_image("cinematic portrait")
        self.assertEqual(img_bytes, b"local_mps_bytes")
        mock_local.generate_image.assert_awaited_once()

    async def test_composite_engine_cascades_to_hf_when_local_fails(self):
        mock_sidecar = AsyncMock(spec=SidecarDiffusionClient)
        mock_sidecar.is_alive.return_value = False

        mock_local = AsyncMock(spec=LocalSDXLClient)
        mock_local.is_available.return_value = True
        mock_local.generate_image.return_value = None  # Failed

        mock_hf = AsyncMock()
        mock_hf.generate_flux.return_value = b"hf_flux_bytes"

        engine = CompositeDiffusionEngine(
            sidecar_client=mock_sidecar,
            local_sdxl=mock_local,
            hf_client=mock_hf
        )

        img_bytes = await engine.generate_image("sci-fi city")
        self.assertEqual(img_bytes, b"hf_flux_bytes")
        mock_hf.generate_flux.assert_awaited_once()

if __name__ == "__main__":
    unittest.main()
