import re
import json
import httpx
from typing import Dict, Any, Optional, List
from app.infrastructure.clients.base import ILLMClient
from app.core.logging import logger

class LocalOfflineLLMClient(ILLMClient):
    """
    High-performance Local Conversational LLM Client (Ollama Qwen 3.5 9B).
    Runs 100% locally on Apple Silicon Metal GPU with strict zero idle memory (keep_alive: 0s).
    Falls back gracefully to offline heuristic if local service is not running.
    """
    def __init__(self, model: str = "qwen3.5:9b", endpoint: str = "http://127.0.0.1:11434"):
        self.model = model
        self.endpoint = endpoint

    async def expand_prompt(self, raw_prompt: str, starter_chip: Optional[str] = None) -> Dict[str, Any]:
        chip_tag = f"[{starter_chip}] " if starter_chip else ""
        clean_raw = f"{chip_tag}{raw_prompt.strip()}"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(
                    f"{self.endpoint}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You are an expert AI visual director for CraftAI Studio. "
                                    "Expand the user's raw prompt into an ultra-realistic, cinematic masterpiece recipe.\n"
                                    "CRITICAL ANATOMICAL & ACCESSORY RULES:\n"
                                    "1. Single accessory rule: If specifying a wristwatch or jewelry, explicitly specify 'single elegant wristwatch on left wrist only, bare right wrist'. Never allow watches on both wrists or dual watches.\n"
                                    "2. Anatomical coherence: Realistic posture, natural hands with five fingers each, coherent limbs.\n"
                                    "Respond ONLY with valid JSON matching: "
                                    '{"master_prompt": string, "negative_prompt": string, "complexity_score": int}'
                                )
                            },
                            {
                                "role": "user",
                                "content": f"Expand this concept: {clean_raw}"
                            }
                        ],
                        "format": "json",
                        "stream": False,
                        "keep_alive": "0s"
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    parsed = json.loads(data["message"]["content"])
                    return {
                        "master_prompt": parsed.get("master_prompt", clean_raw),
                        "negative_prompt": parsed.get("negative_prompt", "blurry, low quality, deformed hands, extra fingers, watches on both wrists, dual watches, two watches, watch on both hands, multiple watches, deformed limbs, extra legs, text, watermark"),
                        "complexity_score": parsed.get("complexity_score", 7),
                        "model_used": f"local/{self.model}"
                    }
        except Exception as e:
            logger.debug(f"[Local LLM] Ollama expand_prompt offline fallback: {e}")

        # Offline heuristic fallback

        cinematic_tokens = "85mm f/1.4 lens, Rembrandt cinematic lighting, award-winning photography, photorealistic textures, volumetric atmosphere, 8k resolution"
        master = f"{clean_raw}, {cinematic_tokens}"
        words = len(master.split())
        score = min(10, max(3, words // 8))

        return {
            "master_prompt": master,
            "negative_prompt": "blurry, low quality, deformed hands, extra fingers, watches on both wrists, dual watches, two watches, deformed limbs, extra legs, text, watermark, oversaturated, amateurish",
            "complexity_score": score,
            "model_used": "local/offline-heuristic"
        }

    async def compile_delta(self, base_prompt: str, user_instruction: str) -> Dict[str, Any]:
        clean_base = base_prompt.strip()
        clean_instruction = user_instruction.strip()

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(
                    f"{self.endpoint}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You are an expert AI visual director for CraftAI Studio image generation. "
                                    "The user provides a base diffusion prompt of an active image and an edit instruction.\n"
                                    "Rules for compiling the updated prompt:\n"
                                    "1. SUBJECT & SCENE LOCK: Maintain 100% fidelity to the core subject identity (age, ethnicity, hairstyle, clothing), environment, camera angle, and scene layout.\n"
                                    "2. ANATOMY & QUALITY FIXES: If the user asks to fix limbs, legs, hands, body parts, posture, or inaccuracies (e.g. 'fix the leg', 'not accurate'): "
                                    "NEVER output conversational phrases like 'fix the leg' or 'not accurate' into the diffusion prompt. "
                                    "Instead, replace or enhance with positive photorealistic visual descriptors: 'perfect anatomically correct posture, natural legs and limbs resting realistically, coherent proportions, sharp photorealistic details'.\n"
                                    "3. CLEAN MODIFICATIONS: Integrate user requested changes seamlessly into the prompt without breaking grammar or repeating keywords.\n"
                                    "4. ACCESSORY COHERENCE: Avoid symmetric hallucinations. If a watch or accessory is present, explicitly specify 'single wristwatch on left wrist only, bare right wrist'. Never allow watches on both hands.\n"
                                    "5. Respond ONLY with valid JSON: "
                                    '{"compiled_prompt": string, "added": list of strings, "removed": list of strings, "suggested_chips": list of 3 short follow-up suggestions}'
                                )
                            },
                            {
                                "role": "user",
                                "content": f"Base prompt: {clean_base}\nUser instruction: {clean_instruction}"
                            }
                        ],
                        "format": "json",
                        "stream": False,
                        "keep_alive": "0s"
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    parsed = json.loads(data["message"]["content"])
                    added_tags = parsed.get("added", [])
                    if isinstance(added_tags, str):
                        added_tags = [added_tags]
                    removed_tags = parsed.get("removed", [])
                    if isinstance(removed_tags, str):
                        removed_tags = [removed_tags]
                    chips = parsed.get("suggested_chips", ["Add depth of field bokeh", "Add cinematic lighting", "Make him wear glasses"])
                    if isinstance(chips, str):
                        chips = [chips]

                    return {
                        "compiled_prompt": parsed.get("compiled_prompt", f"{clean_base}, {clean_instruction}"),
                        "diff": {
                            "added": [t for t in added_tags if t],
                            "removed": [t for t in removed_tags if t]
                        },
                        "suggested_chips": chips[:4],
                        "model_used": f"local/{self.model}",
                        "delta_summary": f"Applied adjustments: '{clean_instruction}'. Refining artwork with preserved subject likeness..."
                    }
        except Exception as e:
            logger.debug(f"[Local LLM] Ollama compile_delta offline fallback: {e}")

        # Offline heuristic fallback
        instruction_body = re.sub(r"^(please\s+|add\s+|make\s+it\s+|is\s+me\s+|karo\s+)", "", clean_instruction, flags=re.IGNORECASE).strip()
        if not instruction_body:
            instruction_body = clean_instruction

        compiled = f"{clean_base}, {instruction_body}, cinematic lighting, 8k"
        added_words = [w for w in instruction_body.split() if len(w) > 3]
        if not added_words:
            added_words = [clean_instruction]

        chips = ["Add Volumetric Smoke", "Moody Low-Key Lighting", "Switch to Anime Style", "Golden Hour Sunlight"]

        return {
            "compiled_prompt": compiled,
            "diff": {
                "added": added_words[:4],
                "removed": []
            },
            "suggested_chips": chips[:3],
            "model_used": "local/offline-heuristic",
            "delta_summary": f"Applied adjustments: '{clean_instruction}'. Refining artwork with preserved subject likeness..."
        }

