from functools import lru_cache
from typing import Optional
from fastapi import Depends
from app.infrastructure.clients.base import ILLMClient, IVisionClient, IDiffusionGateway, IDiffusionEngine
from app.infrastructure.clients.groq_client import GroqClient
from app.infrastructure.clients.gemini_llm_client import GeminiLLMClient
from app.infrastructure.clients.gemini_client import GeminiVisionClient
from app.infrastructure.clients.pollinations_client import PollinationsClient
from app.infrastructure.clients.huggingface_client import HuggingFaceClient
from app.infrastructure.clients.onnx_upscaler_client import OnnxUpscalerClient
from app.infrastructure.clients.sidecar_client import SidecarDiffusionClient
from app.infrastructure.clients.local_sdxl_client import LocalSDXLClient
from app.infrastructure.clients.diffusion_engine import CompositeDiffusionEngine
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

@lru_cache()
def get_sidecar_diffusion_client() -> SidecarDiffusionClient:
    return SidecarDiffusionClient()

@lru_cache()
def get_local_sdxl_client() -> LocalSDXLClient:
    return LocalSDXLClient()

@lru_cache()
def get_diffusion_engine() -> IDiffusionEngine:
    return CompositeDiffusionEngine(
        sidecar_client=get_sidecar_diffusion_client(),
        local_sdxl=get_local_sdxl_client(),
        hf_client=get_huggingface_client()
    )

@lru_cache()
def get_onnx_upscaler_client() -> OnnxUpscalerClient:
    return OnnxUpscalerClient()

@lru_cache()
def get_prompt_service() -> PromptService:
    return PromptService()

def get_vision_service(
    vision_client: IVisionClient = Depends(get_vision_client)
) -> VisionService:
    return VisionService(vision_client=vision_client)

def get_tool_service(
    diffusion_gateway: IDiffusionGateway = Depends(get_diffusion_gateway),
    task_store: ITaskStore = Depends(get_task_store),
    hf_client: HuggingFaceClient = Depends(get_huggingface_client),
    onnx_client: OnnxUpscalerClient = Depends(get_onnx_upscaler_client)
) -> ToolService:
    gateway = diffusion_gateway if isinstance(diffusion_gateway, IDiffusionGateway) else get_diffusion_gateway()
    store = task_store if isinstance(task_store, ITaskStore) else get_task_store()
    hf = hf_client if isinstance(hf_client, HuggingFaceClient) else get_huggingface_client()
    onnx_c = onnx_client if isinstance(onnx_client, OnnxUpscalerClient) else get_onnx_upscaler_client()
    return ToolService(diffusion_gateway=gateway, task_store=store, hf_client=hf, onnx_client=onnx_c)

def get_generation_service(
    diffusion_gateway: IDiffusionGateway = Depends(get_diffusion_gateway),
    diffusion_engine: IDiffusionEngine = Depends(get_diffusion_engine),
    task_store: ITaskStore = Depends(get_task_store),
    vision_client: GeminiVisionClient = Depends(get_vision_client),
    hf_client: HuggingFaceClient = Depends(get_huggingface_client)
) -> GenerationService:
    # Safely handle standalone execution where Depends objects aren't injected by FastAPI
    gateway = diffusion_gateway if isinstance(diffusion_gateway, IDiffusionGateway) else get_diffusion_gateway()
    engine = diffusion_engine if isinstance(diffusion_engine, IDiffusionEngine) else get_diffusion_engine()
    store = task_store if isinstance(task_store, ITaskStore) else get_task_store()
    vision = vision_client if isinstance(vision_client, GeminiVisionClient) else get_vision_client()
    hf = hf_client if isinstance(hf_client, HuggingFaceClient) else get_huggingface_client()

    return GenerationService(
        diffusion_gateway=gateway,
        diffusion_engine=engine,
        task_store=store,
        gemini_vision=vision,
        hf_client=hf
    )

