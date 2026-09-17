import asyncio
import os
import uuid
import httpx
import rembg
from app.infrastructure.clients.base import IDiffusionGateway
from app.infrastructure.storage.task_store import ITaskStore
from app.schemas.tools import ToolPresetRequest, ToolPresetResponse, RemoveBackgroundRequest, RemoveBackgroundResponse
from app.core.supabase_client import get_supabase_admin
from app.core.logging import logger

class ToolService:
    def __init__(self, diffusion_gateway: IDiffusionGateway, task_store: ITaskStore):
        self.diffusion_gateway = diffusion_gateway
        self.task_store = task_store

    async def remove_background(self, req: RemoveBackgroundRequest) -> RemoveBackgroundResponse:
        """Removes background from image on local CPU with rembg (Zero GPU, Zero Tokens, Zero Cost)."""
        task_id = f"tool_rmbg_{uuid.uuid4().hex[:8]}"
        try:
            logger.info(f"[Tool: Background Removal] Processing: {req.image_url}")
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(req.image_url)
                if resp.status_code != 200:
                    raise ValueError(f"Failed to fetch image: HTTP {resp.status_code}")
                input_bytes = resp.content

            # Non-blocking CPU rembg cutout in worker thread
            output_bytes = await asyncio.to_thread(rembg.remove, input_bytes)

            # Upload transparent PNG to Supabase
            admin = get_supabase_admin()
            file_path = f"transparent_cutouts/{uuid.uuid4().hex}.png"
            await asyncio.to_thread(
                admin.storage.from_("user_generations").upload,
                file_path,
                output_bytes,
                {"content-type": "image/png"}
            )
            output_url = admin.storage.from_("user_generations").get_public_url(file_path)

            if self.task_store:
                self.task_store.save_task(task_id, {
                    "status": "completed",
                    "progress": 100,
                    "output_url": output_url,
                    "tier": "Zero-Token CPU Tool"
                })

            logger.info(f"[Tool: Background Removal] Cutout ready: {output_url}")
            return RemoveBackgroundResponse(
                task_id=task_id,
                status="completed",
                output_url=output_url,
                tokens_consumed=0
            )
        except Exception as e:
            logger.error(f"[Tool: Background Removal] Error: {e}")
            return RemoveBackgroundResponse(
                task_id=task_id,
                status="failed",
                output_url=req.image_url,
                tokens_consumed=0
            )

    async def execute_preset_tool(self, req: ToolPresetRequest) -> ToolPresetResponse:
        task_id = f"tool_{req.image_id[:8]}_{os.urandom(3).hex()}"
        output_url = self.diffusion_gateway.build_safe_url(req.target_preset)
        self.task_store.save_task(task_id, {
            "status": "completed",
            "progress": 100,
            "output_url": output_url,
            "tier": "Tier 0 (Free Tool Preset)"
        })
        return ToolPresetResponse(
            task_id=task_id,
            status="completed",
            applied_tool=req.action,
            subject_masked=req.lock_subject,
            tokens_consumed=0,
            output_url=output_url
        )
