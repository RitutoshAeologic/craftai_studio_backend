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
from app.infrastructure.tools import (
    IInpaintEngine,
    IColorizeEngine,
    IBackgroundRemoverEngine,
    IUpscalerEngine,
    ToolEngineFactory
)
from app.services.wallet_service import IWalletService, SupabaseWalletService

@lru_cache()
def get_inpaint_engine() -> IInpaintEngine:
    return ToolEngineFactory.get_inpaint_engine()

@lru_cache()
def get_colorize_engine() -> IColorizeEngine:
    return ToolEngineFactory.get_colorize_engine()

@lru_cache()
def get_bg_remover_engine() -> IBackgroundRemoverEngine:
    return ToolEngineFactory.get_bg_remover_engine()

@lru_cache()
def get_upscaler_engine() -> IUpscalerEngine:
    return ToolEngineFactory.get_upscaler_engine()

@lru_cache()
def get_wallet_service() -> IWalletService:
    return SupabaseWalletService()


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
    onnx_client: OnnxUpscalerClient = Depends(get_onnx_upscaler_client),
    inpaint_engine: IInpaintEngine = Depends(get_inpaint_engine),
    colorize_engine: IColorizeEngine = Depends(get_colorize_engine),
    bg_remover_engine: IBackgroundRemoverEngine = Depends(get_bg_remover_engine),
    upscaler_engine: IUpscalerEngine = Depends(get_upscaler_engine)
) -> ToolService:
    gateway = diffusion_gateway if isinstance(diffusion_gateway, IDiffusionGateway) else get_diffusion_gateway()
    store = task_store if isinstance(task_store, ITaskStore) else get_task_store()
    hf = hf_client if isinstance(hf_client, HuggingFaceClient) else get_huggingface_client()
    onnx_c = onnx_client if isinstance(onnx_client, OnnxUpscalerClient) else get_onnx_upscaler_client()
    inpaint = inpaint_engine if isinstance(inpaint_engine, IInpaintEngine) else get_inpaint_engine()
    colorize = colorize_engine if isinstance(colorize_engine, IColorizeEngine) else get_colorize_engine()
    bg_rem = bg_remover_engine if isinstance(bg_remover_engine, IBackgroundRemoverEngine) else get_bg_remover_engine()
    upscale = upscaler_engine if isinstance(upscaler_engine, IUpscalerEngine) else get_upscaler_engine()
    return ToolService(
        diffusion_gateway=gateway,
        task_store=store,
        hf_client=hf,
        onnx_client=onnx_c,
        inpaint_engine=inpaint,
        colorize_engine=colorize,
        bg_remover_engine=bg_rem,
        upscaler_engine=upscale
    )

def get_generation_service(
    diffusion_gateway: IDiffusionGateway = Depends(get_diffusion_gateway),
    diffusion_engine: IDiffusionEngine = Depends(get_diffusion_engine),
    task_store: ITaskStore = Depends(get_task_store),
    vision_client: GeminiVisionClient = Depends(get_vision_client),
    hf_client: HuggingFaceClient = Depends(get_huggingface_client),
    wallet_service: IWalletService = Depends(get_wallet_service)
) -> GenerationService:
    # Safely handle standalone execution where Depends objects aren't injected by FastAPI
    gateway = diffusion_gateway if isinstance(diffusion_gateway, IDiffusionGateway) else get_diffusion_gateway()
    engine = diffusion_engine if isinstance(diffusion_engine, IDiffusionEngine) else get_diffusion_engine()
    store = task_store if isinstance(task_store, ITaskStore) else get_task_store()
    vision = vision_client if isinstance(vision_client, GeminiVisionClient) else get_vision_client()
    hf = hf_client if isinstance(hf_client, HuggingFaceClient) else get_huggingface_client()

    wallet = wallet_service if isinstance(wallet_service, IWalletService) else get_wallet_service()
    return GenerationService(
        diffusion_gateway=gateway,
        diffusion_engine=engine,
        task_store=store,
        gemini_vision=vision,
        hf_client=hf,
        wallet_service=wallet
    )

