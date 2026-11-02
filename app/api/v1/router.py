from fastapi import APIRouter
from app.api.v1.endpoints.prompt import router as prompt_router
from app.api.v1.endpoints.vision import router as vision_router
from app.api.v1.endpoints.tools import router as tools_router
from app.api.v1.endpoints.generation import router as generation_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.collections import router as collections_router
from app.api.v1.endpoints.search import router as search_router
from app.api.v1.endpoints.remix import router as remix_router
from app.api.v1.endpoints.library import router as library_router

api_v1_router = APIRouter()

# Aggregated sub-routers under /prompt-engineering for mobile & web client compatibility
prompt_engineering_router = APIRouter(prefix="/prompt-engineering")
prompt_engineering_router.include_router(prompt_router)
prompt_engineering_router.include_router(vision_router)
prompt_engineering_router.include_router(tools_router)
prompt_engineering_router.include_router(generation_router)
prompt_engineering_router.include_router(auth_router)
prompt_engineering_router.include_router(collections_router)
prompt_engineering_router.include_router(search_router)
prompt_engineering_router.include_router(remix_router)
prompt_engineering_router.include_router(library_router)

api_v1_router.include_router(prompt_engineering_router)

# Direct root aliasing to prevent 404 on web clients calling without /prompt-engineering prefix
api_v1_router.include_router(vision_router)
api_v1_router.include_router(tools_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(collections_router)
api_v1_router.include_router(search_router)
api_v1_router.include_router(remix_router)
api_v1_router.include_router(library_router)
api_v1_router.include_router(generation_router)
api_v1_router.include_router(prompt_router)


@api_v1_router.get("/health", tags=["Health"])
def api_v1_health():
    return {
        "status": "healthy",
        "service": "CraftAI Studio Backend",
        "version": "1.0.0"
    }
