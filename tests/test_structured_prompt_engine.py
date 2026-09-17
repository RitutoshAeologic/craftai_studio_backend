import asyncio
import unittest
from app.core.prompt_compiler import PromptCompiler, OPTION_A_PREFIX
from app.infrastructure.clients.local_llm_client import LocalOfflineLLMClient
from app.services.prompt_service import PromptService
from app.schemas.generation import GenerationDispatchRequest

class TestStructuredPromptEngine(unittest.TestCase):
    def setUp(self):
        self.sample_metadata = {
            "subject": "cybernetic samurai warrior with glowing katana",
            "environment": "rain-soaked neo-Tokyo alleyway at twilight",
            "lighting": "vibrant pink neon rim lighting and volumetric mist",
            "camera_optics": "85mm f/1.4 portrait lens, shallow depth of field",
            "art_style": "cinematic 35mm film still",
            "avoid": ["cartoon", "3d render", "lowres", "watermark"],
            "preserved_elements": ["subject"]
        }

    def test_flux_compilation(self):
        compiled = PromptCompiler.compile_for_flux(self.sample_metadata)
        self.assertIn("Cinematic 35mm film still", compiled)
        self.assertIn("featuring cybernetic samurai warrior with glowing katana", compiled)
        self.assertIn("set in rain-soaked neo-Tokyo alleyway at twilight", compiled)
        self.assertIn("illuminated with vibrant pink neon rim lighting", compiled)
        self.assertIn("captured on 85mm f/1.4 portrait lens", compiled)

    def test_flux_option_a_prefix_preservation(self):
        fallback = f"{OPTION_A_PREFIX}add cherry blossoms"
        compiled = PromptCompiler.compile_for_flux(self.sample_metadata, fallback_prompt=fallback)
        self.assertTrue(compiled.startswith(OPTION_A_PREFIX))

    def test_sdxl_compilation(self):
        pos, neg = PromptCompiler.compile_for_sdxl(self.sample_metadata)
        self.assertIn("cybernetic samurai warrior with glowing katana", pos)
        self.assertIn("cartoon", neg)
        self.assertIn("blurry", neg)
        self.assertIn("extra limbs", neg)

    def test_merge_structured_deltas_preserves_locked(self):
        delta = {
            "lighting": "golden hour sunset glow",
            "subject": "a regular dog", # Should be ignored because subject is preserved
            "avoid": ["snow"]
        }
        merged = PromptCompiler.merge_structured_deltas(self.sample_metadata, delta)
        # Subject should remain the samurai
        self.assertEqual(merged["subject"], "cybernetic samurai warrior with glowing katana")
        # Lighting should be updated
        self.assertEqual(merged["lighting"], "golden hour sunset glow")
        # Avoid should include both old and new
        self.assertIn("snow", merged["avoid"])
        self.assertIn("cartoon", merged["avoid"])

    def test_local_offline_llm_expand_structured(self):
        client = LocalOfflineLLMClient()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            res = loop.run_until_complete(client.expand_prompt("cyberpunk cat"))
            self.assertIn("master_prompt", res)
            self.assertIn("structured_metadata", res)
            meta = res["structured_metadata"]
            self.assertEqual(meta["subject"], "cyberpunk cat")
            self.assertIn("blurry", meta["avoid"])
        finally:
            loop.close()

    def test_local_offline_llm_delta_structured(self):
        client = LocalOfflineLLMClient()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            res = loop.run_until_complete(client.compile_delta("cyberpunk cat", "add neon rain"))
            self.assertIn("compiled_prompt", res)
            self.assertIn("diff", res)
            self.assertIn("structured_metadata", res)
        finally:
            loop.close()

if __name__ == '__main__':
    unittest.main()
