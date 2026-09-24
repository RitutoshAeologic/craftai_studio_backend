from fastapi import APIRouter
from app.api.v1.endpoints.prompt import router as prompt_router
from app.api.v1.endpoints.vision import router as vision_router
from app.api.v1.endpoints.tools import router as tools_router
from app.api.v1.endpoints.generation import router as generation_router
from app.api.v1.endpoints.remix import router as remix_router
from app.api.v1.endpoints.library import router as library_router

api_v1_router = APIRouter()

# Aggregated sub-routers under /prompt-engineering for clean separation of concerns
prompt_engineering_router = APIRouter(prefix="/prompt-engineering")
prompt_engineering_router.include_router(prompt_router)
prompt_engineering_router.include_router(vision_router)
prompt_engineering_router.include_router(tools_router)
prompt_engineering_router.include_router(generation_router)
prompt_engineering_router.include_router(remix_router)
prompt_engineering_router.include_router(library_router)

api_v1_router.include_router(prompt_engineering_router)

# Direct root aliasing for vision, tools, and remix to prevent 404 on clients calling without /prompt-engineering prefix
api_v1_router.include_router(vision_router)
api_v1_router.include_router(tools_router)
api_v1_router.include_router(remix_router)
api_v1_router.include_router(library_router)

@api_v1_router.get("/health", tags=["Health"])
def api_v1_health():
    return {
        "status": "healthy",
        "service": "CraftAI Studio Backend",
        "version": "1.0.0"
    }
