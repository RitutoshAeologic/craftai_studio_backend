"""
CraftAI Studio — Standalone Local Diffusion Sidecar Worker
Runs on port 8001 as an isolated microservice on Apple Silicon M1 Pro (MPS).
Decouples heavy PyTorch / SDXL model weights from the main FastAPI server (port 8000),
guaranteeing instant `uvicorn --reload` cycles during backend development.

Usage:
    .venv/bin/python scripts/diffusion_sidecar.py
"""

import sys
import os
from pathlib import Path

# Add project root to sys.path so app modules import cleanly
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional

from app.core.config import settings
from app.core.logging import logger
from app.infrastructure.clients.local_sdxl_client import LocalSDXLClient

sidecar_app = FastAPI(
    title="CraftAI Studio — Local Diffusion Sidecar",
    description="Dedicated PyTorch Metal (MPS) Worker for SDXL-Lightning & RealVisXL v4.0",
    version="1.0.0"
)

import asyncio

# Global client singleton in sidecar process
sdxl_client: Optional[LocalSDXLClient] = None
# Concurrency lock to prevent concurrent MPS kernel conflicts on Apple Silicon
sidecar_lock = asyncio.Lock()

class SidecarGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    width: Optional[int] = Field(default=1024, ge=512, le=2048)
    height: Optional[int] = Field(default=1024, ge=512, le=2048)
    seed: Optional[int] = Field(default=42)
    negative_prompt: Optional[str] = Field(default=None)

@sidecar_app.on_event("startup")
async def startup_event():
    global sdxl_client
    logger.info("[Sidecar Startup] Initializing Local SDXL Engine on Apple Silicon MPS...")
    sdxl_client = LocalSDXLClient()
    logger.info("[Sidecar Startup] Sidecar engine ready to accept inference requests.")

@sidecar_app.get("/health")
async def sidecar_health():
    is_ready = sdxl_client is not None and sdxl_client.is_available()
    return {
        "status": "ready" if is_ready else "initializing",
        "service": "CraftAI Local Diffusion Sidecar",
        "device": sdxl_client._device if sdxl_client else "unknown",
        "base_model": settings.LOCAL_SDXL_BASE_MODEL,
        "lora_repo": settings.LOCAL_SDXL_LORA_REPO,
        "steps": settings.LOCAL_SDXL_STEPS
    }

@sidecar_app.post("/generate")
async def sidecar_generate(req: SidecarGenerateRequest):
    if not sdxl_client:
        raise HTTPException(status_code=503, detail="Local diffusion engine is still initializing.")

    async with sidecar_lock:
        img_bytes = await sdxl_client.generate_image(
            prompt=req.prompt,
            width=req.width or 1024,
            height=req.height or 1024,
            seed=req.seed or 42,
            negative_prompt=req.negative_prompt
        )

        try:
            import torch
            if torch.backends.mps.is_available() and hasattr(torch, "mps"):
                torch.mps.empty_cache()
        except Exception:
            pass

    if not img_bytes:
        raise HTTPException(status_code=500, detail="Inference failed on local engine.")

    return Response(content=img_bytes, media_type="image/png")

if __name__ == "__main__":
    port = int(os.environ.get("SIDECAR_PORT", 8001))
    print(f"🚀 Starting CraftAI Diffusion Sidecar on http://127.0.0.1:{port}...")
    uvicorn.run("scripts.diffusion_sidecar:sidecar_app", host="127.0.0.1", port=port, reload=False)
