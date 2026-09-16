import re
import json
from typing import Dict, Any

def clean_and_parse_llm_json(raw_text: str) -> Dict[str, Any]:
    """
    Robust JSON parser for diverse Multi-LLM outputs (Gemini, Groq, Claude, DeepSeek, GPT).
    Features:
    - Strips DeepSeek reasoning chains (<think>...</think>)
    - Extracts JSON from markdown code blocks (```json ... ```)
    - Locates outermost JSON object braces { ... }
    - Gracefully cleans trailing commas
    """
    if not raw_text:
        return {}

    # 1. Strip reasoning thoughts (DeepSeek R1 / Qwen thinking tags)
    text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL).strip()

    # 2. Extract content within markdown code fences if present
    md_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', text)
    if md_match:
        text = md_match.group(1).strip()
    else:
        # 3. Locate the outermost JSON object
        first_brace = text.find('{')
        last_brace = text.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            text = text[first_brace:last_brace + 1].strip()

    # 4. Attempt standard JSON parsing
    try:
        return json.loads(text)
    except Exception:
        pass

    # 5. Resilient recovery: remove trailing commas before closing braces/brackets
    try:
        cleaned = re.sub(r',\s*([\}\]])', r'\1', text)
        return json.loads(cleaned)
    except Exception:
        return {}
