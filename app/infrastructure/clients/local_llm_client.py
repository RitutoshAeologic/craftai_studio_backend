import re
from typing import Dict, Any, Optional, List
from app.infrastructure.clients.base import ILLMClient

class LocalOfflineLLMClient(ILLMClient):
    """
    Deterministic, zero-cost, offline rule-based prompt compiler and delta synthesiser.
    Guarantees 100% system availability with zero latency and zero external dependencies.
    """
    def __init__(self, model: str = "offline-cinematic-engine"):
        self.model = model

    async def expand_prompt(self, raw_prompt: str, starter_chip: Optional[str] = None) -> Dict[str, Any]:
        chip_tag = f"[{starter_chip}] " if starter_chip else ""
        clean_raw = raw_prompt.strip()

        is_edit_image = clean_raw.startswith("Edit image1 as follows: ")
        if is_edit_image:
            edit_content = clean_raw[len("Edit image1 as follows: "):].strip()
            master = f"Edit image1 as follows: {edit_content}, seamless photographic blending, 85mm f/1.4 lens, cinematic lighting, 8k resolution, photorealistic textures"
            subject_str = edit_content
        else:
            cinematic_tokens = "85mm f/1.4 lens, Rembrandt cinematic lighting, award-winning photography, photorealistic textures, volumetric atmosphere, octane render, 8k resolution"
            master = f"{chip_tag}{clean_raw}, {cinematic_tokens}"
            subject_str = clean_raw

        words = len(master.split())
        score = min(10, max(3, words // 8))

        metadata = {
            "subject": subject_str,
            "environment": starter_chip or "cinematic scene",
            "lighting": "Rembrandt cinematic lighting, volumetric atmosphere",
            "camera_optics": "85mm f/1.4 lens, shallow depth of field",
            "art_style": "photorealistic award-winning photography",
            "avoid": ["blurry", "low quality", "deformed hands", "extra fingers", "text", "watermark"],
            "preserved_elements": []
        }

        return {
            "master_prompt": master,
            "negative_prompt": "blurry, low quality, deformed hands, extra fingers, text, watermark, oversaturated, amateurish",
            "complexity_score": score,
            "structured_metadata": metadata,
            "model_used": f"local/{self.model}"
        }

    async def compile_delta(self, base_prompt: str, user_instruction: str) -> Dict[str, Any]:
        clean_base = base_prompt.strip()
        clean_instruction = user_instruction.strip()
        is_edit = clean_base.startswith("Edit image1 as follows: ")

        # Clean noise words from instruction
        instruction_body = re.sub(r"^(please\s+|add\s+|make\s+it\s+|is\s+me\s+|karo\s+)", "", clean_instruction, flags=re.IGNORECASE).strip()
        if not instruction_body:
            instruction_body = clean_instruction

        if is_edit:
            compiled = f"{clean_base}, {instruction_body}, cinematic lighting, photorealistic textures"
        else:
            compiled = f"{clean_base}, {instruction_body}, cinematic lighting, 8k"

        added_words = [w for w in instruction_body.split() if len(w) > 3]
        if not added_words:
            added_words = [clean_instruction]

        chips = ["Add Volumetric Smoke", "Moody Low-Key Lighting", "Switch to Anime Style", "Golden Hour Sunlight"]

        metadata = {
            "subject": clean_base,
            "environment": instruction_body,
            "lighting": "cinematic lighting, rim lights",
            "camera_optics": "85mm lens, f/1.4",
            "art_style": "cinematic photorealism",
            "avoid": ["blurry", "low quality", "distorted"],
            "preserved_elements": []
        }

        return {
            "compiled_prompt": compiled,
            "diff": {
                "added": added_words[:4],
                "removed": []
            },
            "suggested_chips": chips[:3],
            "structured_metadata": metadata,
            "model_used": f"local/{self.model}"
        }
