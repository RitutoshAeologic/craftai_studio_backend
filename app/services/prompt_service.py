from typing import Optional
from app.infrastructure.clients.base import ILLMClient
from app.schemas.prompt import PromptExpandResponse, PromptDeltaResponse, PromptDeltaDiff
from app.services.tokenizer import calculate_complexity_charge

class PromptService:
    def __init__(self, groq_client: ILLMClient, gemini_client: Optional[ILLMClient] = None):
        self.groq_client = groq_client
        self.gemini_client = gemini_client or groq_client

    def _get_client(self, ai_model: str) -> ILLMClient:
        if ai_model and "gemini" in ai_model.lower():
            return self.gemini_client
        return self.groq_client

    async def expand_prompt(
        self,
        raw_prompt: str,
        starter_chip: Optional[str] = None,
        aspect_ratio: str = "1:1",
        ai_model: str = "groq"
    ) -> PromptExpandResponse:
        client = self._get_client(ai_model)
        res = await client.expand_prompt(raw_prompt, starter_chip)
        word_count = len(res["master_prompt"].split())
        complexity_score = int(calculate_complexity_charge(
            model="flux",
            word_count=word_count,
            aspect_ratio=aspect_ratio,
            is_magic_expanded=True
        ))
        return PromptExpandResponse(
            master_prompt=res["master_prompt"],
            negative_prompt=res["negative_prompt"],
            complexity_score=complexity_score,
            model_used=res["model_used"]
        )

    async def compile_delta(
        self,
        base_prompt: str,
        user_instruction: str,
        ai_model: str = "groq"
    ) -> PromptDeltaResponse:
        client = self._get_client(ai_model)
        res = await client.compile_delta(base_prompt, user_instruction)
        diff_data = res.get("diff", {})
        return PromptDeltaResponse(
            compiled_prompt=res["compiled_prompt"],
            diff=PromptDeltaDiff(
                added=diff_data.get("added", []),
                removed=diff_data.get("removed", [])
            ),
            suggested_chips=res.get("suggested_chips", []),
            model_used=res["model_used"]
        )
