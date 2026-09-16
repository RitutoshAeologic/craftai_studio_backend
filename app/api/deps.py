from functools import lru_cache
from typing import Optional
from fastapi import Depends
from app.infrastructure.clients.base import ILLMClient, IVisionClient, IDiffusionGateway
from app.infrastructure.clients.groq_client import GroqClient
from app.infrastructure.clients.gemini_llm_client import GeminiLLMClient
from app.infrastructure.clients.gemini_client import GeminiVisionClient
from app.infrastructure.clients.pollinations_client import PollinationsClient
from app.infrastructure.clients.huggingface_client import HuggingFaceClient
from app.infrastructure.storage.task_store import ITaskStore, ThreadSafeInMemoryTaskStore
from app.services.prompt_service import PromptService
from app.services.vision_service import VisionService
from app.services.tool_service import ToolService
from app.services.generation_service import GenerationService

@lru_cache()
def get_task_store() -> ITaskStore:
    return ThreadSafeInMemoryTaskStore()

@lru_cache()
def get_groq_client() -> ILLMClient:
    return GroqClient()

@lru_cache()
def get_gemini_llm_client() -> ILLMClient:
    return GeminiLLMClient()

@lru_cache()
def get_vision_client() -> GeminiVisionClient:
    return GeminiVisionClient()

@lru_cache()
def get_diffusion_gateway() -> IDiffusionGateway:
    return PollinationsClient()

@lru_cache()
def get_huggingface_client() -> HuggingFaceClient:
    return HuggingFaceClient()

def get_prompt_service(
    groq_client: ILLMClient = Depends(get_groq_client),
    gemini_client: ILLMClient = Depends(get_gemini_llm_client)
) -> PromptService:
    return PromptService(groq_client=groq_client, gemini_client=gemini_client)

def get_vision_service(
    vision_client: IVisionClient = Depends(get_vision_client)
) -> VisionService:
    return VisionService(vision_client=vision_client)

def get_tool_service(
    diffusion_gateway: IDiffusionGateway = Depends(get_diffusion_gateway),
    task_store: ITaskStore = Depends(get_task_store)
) -> ToolService:
    return ToolService(diffusion_gateway=diffusion_gateway, task_store=task_store)

def get_generation_service(
    diffusion_gateway: IDiffusionGateway = Depends(get_diffusion_gateway),
    task_store: ITaskStore = Depends(get_task_store),
    vision_client: GeminiVisionClient = Depends(get_vision_client),
    hf_client: HuggingFaceClient = Depends(get_huggingface_client)
) -> GenerationService:
    # Safely handle standalone execution where Depends objects aren't injected by FastAPI
    gateway = diffusion_gateway if isinstance(diffusion_gateway, IDiffusionGateway) else get_diffusion_gateway()
    store = task_store if isinstance(task_store, ITaskStore) else get_task_store()
    vision = vision_client if isinstance(vision_client, GeminiVisionClient) else get_vision_client()
    hf = hf_client if isinstance(hf_client, HuggingFaceClient) else get_huggingface_client()

    return GenerationService(
        diffusion_gateway=gateway,
        task_store=store,
        gemini_vision=vision,
        hf_client=hf
    )
