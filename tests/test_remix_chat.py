import unittest
from fastapi.testclient import TestClient
from app.main import app

class TestRemixChatEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_create_remix_session_and_chat(self):
        # 1. Create a session
        payload = {
            "anchor_image_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb",
            "source_type": "explore",
            "remixed_from_prompt_id": "11111111-2222-3333-4444-555555555555",
            "initial_prompt": "Cyberpunk warrior portrait",
            "style_weight": 0.65
        }
        res = self.client.post("/api/v1/prompt-engineering/remix/sessions", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        session = data["session"]
        messages = data["messages"]
        session_id = session["id"]

        self.assertEqual(session["anchor_image_url"], payload["anchor_image_url"])
        self.assertEqual(session["style_weight"], 0.65)
        self.assertGreaterEqual(len(messages), 1)
        self.assertEqual(messages[0]["role"], "assistant")

        # 2. Fetch session history
        hist_res = self.client.get(f"/api/v1/prompt-engineering/remix/sessions/{session_id}")
        self.assertEqual(hist_res.status_code, 200)
        self.assertEqual(hist_res.json()["session"]["id"], session_id)

        # 3. Chat turn
        chat_req = {
            "session_id": session_id,
            "user_instruction": "Add vibrant neon rain, volumetric atmospheric fog, and cinematic lens flare",
            "ai_model": "local",
            "style_weight": 0.70
        }
        chat_res = self.client.post("/api/v1/prompt-engineering/remix/chat", json=chat_req)
        self.assertEqual(chat_res.status_code, 200)
        chat_data = chat_res.json()
        self.assertEqual(chat_data["session_id"], session_id)
        self.assertEqual(chat_data["user_message"]["content"], chat_req["user_instruction"])
        self.assertEqual(chat_data["assistant_message"]["role"], "assistant")
        self.assertIn("compiled_prompt", chat_data)
        self.assertGreaterEqual(chat_data["turn_count"], 1)

if __name__ == "__main__":
    unittest.main()
