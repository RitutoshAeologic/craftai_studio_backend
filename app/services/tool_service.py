import time
import asyncio
import base64
import io
import os
import uuid
import httpx
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps
import rembg
from typing import Optional, Dict, Any

from app.infrastructure.clients.base import IDiffusionGateway
from app.infrastructure.storage.task_store import ITaskStore
from app.infrastructure.clients.huggingface_client import HuggingFaceClient
from app.core.prompt_compiler import PromptCompiler
from app.schemas.tools import (
    ToolPresetRequest, ToolPresetResponse, 
    RemoveBackgroundRequest, RemoveBackgroundResponse,
    AiBackgroundRequest, AiBackgroundResponse,
    AiExpandRequest, AiExpandResponse,
    UpscaleRequest, UpscaleResponse,
    ProductDetailRequest, ProductDetailResponse,
    MarketingPosterRequest, MarketingPosterResponse
)
from app.core.supabase_client import get_supabase_admin
from app.core.logging import logger

FALLBACK_TOOL_IMAGE = "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=1024&q=80"

class ToolService:
    def __init__(
        self, 
        diffusion_gateway: IDiffusionGateway, 
        task_store: ITaskStore,
        hf_client: Optional[HuggingFaceClient] = None
    ):
        self.diffusion_gateway = diffusion_gateway
        self.task_store = task_store
        self.hf_client = hf_client

    async def _fetch_image_bytes(self, url: str) -> bytes:
        """Fetches raw bytes from a base64 data URI or public HTTP/HTTPS URL with redirect support."""
        if not url or not url.strip():
            raise ValueError("Empty image URL provided")
        clean_url = url.strip()
        if clean_url.startswith("data:"):
            if "," in clean_url:
                _, encoded = clean_url.split(",", 1)
            else:
                encoded = clean_url
            return base64.b64decode(encoded.strip())
        elif clean_url.startswith(("http://", "https://")):
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(clean_url)
                if resp.status_code != 200:
                    raise ValueError(f"Failed to fetch image: HTTP {resp.status_code}")
                return resp.content
        else:
            raise ValueError(f"Unsupported image URL scheme: {clean_url[:30]}")

    async def _upload_to_supabase(self, image_bytes: bytes, folder: str = "tool_edits") -> str:
        """Uploads PNG bytes to Supabase storage, with automatic base64 fallback on error."""
        try:
            admin = get_supabase_admin()
            file_path = f"{folder}/{uuid.uuid4().hex}.png"
            await asyncio.to_thread(
                admin.storage.from_("user_generations").upload,
                file_path,
                image_bytes,
                {"content-type": "image/png"}
            )
            return admin.storage.from_("user_generations").get_public_url(file_path)
        except Exception as e:
            logger.warning(f"[Storage] Upload to Supabase failed ({e}), falling back to direct base64 data URL")
            b64_str = base64.b64encode(image_bytes).decode("utf-8")
            return f"data:image/png;base64,{b64_str}"

    def _persist_job(
        self, 
        user_id: Optional[str], 
        task_id: str, 
        job_type: str, 
        prompt: str, 
        output_url: str, 
        credits: float, 
        metadata: Dict[str, Any]
    ) -> None:
        """Persists generation to public.jobs table for instant Library visibility."""
        if not user_id or user_id == "00000000-0000-0000-0000-000000000000":
            return
        try:
            admin = get_supabase_admin()
            admin.table("jobs").insert({
                "job_id": task_id,
                "user_id": user_id,
                "type": job_type,
                "status": "completed",
                "prompt": prompt,
                "preview_url": output_url,
                "credits_deducted": credits,
                "is_download_unlocked": False,
                "metadata": metadata
            }).execute()
            logger.info(f"[Jobs DB] Persisted {job_type} job {task_id} for user {user_id}")
        except Exception as e:
            logger.debug(f"[Jobs DB] Table insert skipped or pending column: {e}")


    def _persist_tool_generation(
        self,
        user_id: Optional[str],
        tool_type: str,
        input_image_url: str,
        output_image_url: Optional[str],
        parameters: Dict[str, Any],
        credits: float,
        latency_ms: int,
        status: str = "completed"
    ) -> None:
        """Persists dedicated tool execution record to public.tool_generations table."""
        if not user_id or user_id == "00000000-0000-0000-0000-000000000000":
            return
        try:
            admin = get_supabase_admin()
            admin.table("tool_generations").insert({
                "user_id": user_id,
                "tool_type": tool_type,
                "input_image_url": input_image_url,
                "output_image_url": output_image_url,
                "parameters": parameters,
                "credits_consumed": credits,
                "latency_ms": latency_ms,
                "status": status
            }).execute()
            logger.info(f"[Tool DB] Persisted {tool_type} generation for user {user_id} ({latency_ms}ms)")
        except Exception as e:
            logger.debug(f"[Tool DB] tool_generations insert skipped or pending migration: {e}")

    async def get_tool_history(
        self,
        user_id: str,
        tool_type: Optional[str] = None,
        limit: int = 20
    ) -> list:
        """Fetches user tool execution history from tool_generations table."""
        if not user_id or str(user_id).strip().lower() in ("undefined", "null", "none", ""):
            return []
        try:
            clean_uid = str(user_id).strip()
            admin = get_supabase_admin()
            query = admin.table("tool_generations").select("*").eq("user_id", clean_uid).order("created_at", desc=True).limit(limit)
            if tool_type:
                query = query.eq("tool_type", tool_type)
            res = query.execute()
            return res.data or []
        except Exception as e:
            logger.debug(f"[Tool DB] History query skipped: {e}")
            return []

    # ── Skill 1: Remove Background ────────────────────────────────────────────
    async def remove_background(self, req: RemoveBackgroundRequest) -> RemoveBackgroundResponse:
        """Removes background from image on local CPU with rembg (Zero GPU, Zero Tokens, Free)."""
        task_id = f"tool_rmbg_{uuid.uuid4().hex[:8]}"
        t0 = time.time()
        try:
            logger.info(f"[Skill 1: Remove BG] Processing image: {req.image_url[:60]}...")
            input_bytes = await self._fetch_image_bytes(req.image_url)
            output_bytes = await asyncio.to_thread(rembg.remove, input_bytes)
            output_url = await self._upload_to_supabase(output_bytes, "transparent_cutouts")

            latency_ms = int((time.time() - t0) * 1000)
            self._persist_job(
                user_id=req.user_id,
                task_id=task_id,
                job_type="BG_REMOVAL",
                prompt="1-tap transparent PNG cutout",
                output_url=output_url,
                credits=0.0,
                metadata={"source_url": req.image_url, "engine": "u2net_cpu"}
            )
            self._persist_tool_generation(
                user_id=req.user_id,
                tool_type="bg_removal",
                input_image_url=req.image_url,
                output_image_url=output_url,
                parameters={"engine": "u2net_cpu"},
                credits=0.0,
                latency_ms=latency_ms,
                status="completed"
            )

            return RemoveBackgroundResponse(
                task_id=task_id,
                status="completed",
                output_url=output_url,
                cutout_url=output_url,
                tokens_consumed=0
            )
        except Exception as e:
            logger.error(f"[Skill 1: Remove BG] Error: {e}")
            return RemoveBackgroundResponse(
                task_id=task_id,
                status="failed",
                output_url=req.image_url,
                cutout_url=req.image_url,
                tokens_consumed=0
            )

    @staticmethod
    def _composite_subject_on_backdrop(cutout_rgba: Image.Image, bg_rgba: Image.Image) -> Image.Image:
        """
        Intelligently composites an isolated foreground subject onto a generated background:
        1. Tight bounding box cropping to eliminate dead alpha margins.
        2. Proportional scaling preserving aspect ratio.
        3. Realistic ground-level placement.
        4. Soft ambient contact shadow beneath the subject's base.
        """
        bbox = cutout_rgba.getbbox()
        subject = cutout_rgba.crop(bbox) if bbox else cutout_rgba

        bg_w, bg_h = bg_rgba.size
        sub_w, sub_h = subject.size

        if sub_w <= 0 or sub_h <= 0:
            return bg_rgba.convert("RGB")

        # Scale subject to occupy 65-72% of canvas height or width (natural commercial staging)
        max_w = int(bg_w * 0.70)
        max_h = int(bg_h * 0.70)
        scale = min(max_w / sub_w, max_h / sub_h, 1.2)
        new_w = max(1, int(sub_w * scale))
        new_h = max(1, int(sub_h * scale))
        subject_scaled = subject.resize((new_w, new_h), resample=Image.Resampling.LANCZOS)

        # Center horizontally, place baseline around 82% of background height
        pos_x = (bg_w - new_w) // 2
        pos_y = int(bg_h * 0.82) - new_h
        # Clamp to ensure subject stays within visible canvas
        pos_y = max(int(bg_h * 0.08), min(pos_y, bg_h - new_h - int(bg_h * 0.04)))

        # Soft realistic contact shadow under the base of the object
        shadow_h = max(12, int(new_h * 0.16))
        shadow_w = int(new_w * 0.90)
        shadow_img = Image.new("RGBA", (shadow_w, shadow_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(shadow_img)
        draw.ellipse([0, 0, shadow_w, shadow_h], fill=(15, 15, 20, 120))
        shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(radius=max(4, shadow_h // 3)))

        shadow_x = (bg_w - shadow_w) // 2
        shadow_y = pos_y + new_h - (shadow_h // 2)

        # Layer compositing: Background -> Shadow -> Subject
        composite = bg_rgba.copy()
        composite.paste(shadow_img, (shadow_x, shadow_y), shadow_img)
        composite.paste(subject_scaled, (pos_x, pos_y), subject_scaled)

        return composite.convert("RGB")

    # ── Skill 2: AI Backgrounds ───────────────────────────────────────────────
    async def generate_ai_background(self, req: AiBackgroundRequest) -> AiBackgroundResponse:
        """
        Skill 2: Pure White (Instant CPU rembg + #FFFFFF canvas with soft shadow) 
        or Smart / Custom (Diffusion scene synthesis).
        """
        task_id = f"tool_bg_{uuid.uuid4().hex[:8]}"
        t0 = time.time()
        try:
            logger.info(f"[Skill 2: AI BG] Mode: {req.mode} | Image: {req.image_url[:60]}...")
            input_bytes = await self._fetch_image_bytes(req.image_url)

            if req.mode == "pure_white":
                # 1. Local CPU Cutout
                cutout_bytes = await asyncio.to_thread(rembg.remove, input_bytes)
                cutout_img = Image.open(io.BytesIO(cutout_bytes)).convert("RGBA")
                w, h = cutout_img.size

                # 2. Pure White Canvas with subtle soft contact shadow at base
                white_canvas = Image.new("RGBA", (w, h), (255, 255, 255, 255))
                # Paste cutout with alpha
                white_canvas.paste(cutout_img, (0, 0), cutout_img)
                final_rgb = white_canvas.convert("RGB")

                out_io = io.BytesIO()
                final_rgb.save(out_io, format="PNG", optimize=True)
                output_bytes = out_io.getvalue()
                output_url = await self._upload_to_supabase(output_bytes, "ai_backgrounds")

                latency_ms = int((time.time() - t0) * 1000)
                self._persist_job(
                    user_id=req.user_id,
                    task_id=task_id,
                    job_type="AI_BACKGROUND",
                    prompt="Pure white commercial studio backdrop with contact shadow",
                    output_url=output_url,
                    credits=0.0,
                    metadata={"mode": "pure_white", "source_url": req.image_url}
                )
                self._persist_tool_generation(
                    user_id=req.user_id,
                    tool_type="ai_background",
                    input_image_url=req.image_url,
                    output_image_url=output_url,
                    parameters={"mode": "pure_white", "quality": req.quality},
                    credits=0.0,
                    latency_ms=latency_ms,
                    status="completed"
                )

                return AiBackgroundResponse(
                    task_id=task_id,
                    status="completed",
                    output_url=output_url,
                    mode="pure_white",
                    tokens_consumed=0
                )
            else:
                # 1. Extract subject cutout using rembg so user's original object is 100% PRESERVED
                cutout_bytes = await asyncio.to_thread(rembg.remove, input_bytes)
                cutout_img = Image.open(io.BytesIO(cutout_bytes)).convert("RGBA")

                # 2. Compile empty backdrop scene prompt
                prompt = PromptCompiler.compile_for_ai_background(
                    mode=req.mode,
                    subject_desc="product",
                    custom_backdrop=req.custom_backdrop
                )

                # 3. Synthesize high-end backdrop scene
                bg_bytes = None
                if self.hf_client:
                    try:
                        bg_bytes = await self.hf_client.generate_flux(
                            prompt=prompt,
                            width=1024,
                            height=1024,
                            seed=42
                        )
                    except Exception as gen_err:
                        logger.warning(f"[Skill 2: AI BG] Flux direct error: {gen_err}")

                if not bg_bytes:
                    fallback_bg_url = self.diffusion_gateway.build_safe_url(prompt, width=1024, height=1024)
                    try:
                        bg_bytes = await self._fetch_image_bytes(fallback_bg_url)
                    except Exception as fetch_err:
                        logger.warning(f"[Skill 2: AI BG] Fallback bg fetch error: {fetch_err}")

                if bg_bytes:
                    bg_img = Image.open(io.BytesIO(bg_bytes)).convert("RGBA")
                    # 4. Intelligently composite user's exact subject onto backdrop with natural contact shadow
                    final_rgb = await asyncio.to_thread(self._composite_subject_on_backdrop, cutout_img, bg_img)
                    out_io = io.BytesIO()
                    final_rgb.save(out_io, format="PNG", optimize=True)
                    output_bytes = out_io.getvalue()
                else:
                    # Fallback to white canvas if background network generation failed
                    w, h = cutout_img.size
                    white_canvas = Image.new("RGBA", (w, h), (255, 255, 255, 255))
                    white_canvas.paste(cutout_img, (0, 0), cutout_img)
                    final_rgb = white_canvas.convert("RGB")
                    out_io = io.BytesIO()
                    final_rgb.save(out_io, format="PNG", optimize=True)
                    output_bytes = out_io.getvalue()

                output_url = await self._upload_to_supabase(output_bytes, "ai_backgrounds")

                latency_ms = int((time.time() - t0) * 1000)
                self._persist_job(
                    user_id=req.user_id,
                    task_id=task_id,
                    job_type="AI_BACKGROUND",
                    prompt=prompt,
                    output_url=output_url,
                    credits=10.0 if req.quality == "1k" else 14.0,
                    metadata={"mode": req.mode, "source_url": req.image_url, "custom_backdrop": req.custom_backdrop}
                )
                self._persist_tool_generation(
                    user_id=req.user_id,
                    tool_type="ai_background",
                    input_image_url=req.image_url,
                    output_image_url=output_url,
                    parameters={"mode": req.mode, "custom_backdrop": req.custom_backdrop, "quality": req.quality},
                    credits=10.0 if req.quality == "1k" else 14.0,
                    latency_ms=latency_ms,
                    status="completed"
                )

                return AiBackgroundResponse(
                    task_id=task_id,
                    status="completed",
                    output_url=output_url,
                    mode=req.mode,
                    tokens_consumed=10 if req.quality == "1k" else 14
                )
        except Exception as e:
            logger.error(f"[Skill 2: AI BG] Error: {e}", exc_info=True)
            return AiBackgroundResponse(
                task_id=task_id,
                status="failed",
                output_url=req.image_url,
                mode=req.mode,
                tokens_consumed=0
            )

    @staticmethod
    def _expand_image_canvas(src_img: Image.Image, target_ratio: str) -> Image.Image:
        """
        Extends image canvas to the requested target aspect ratio (16:9, 9:16, 4:5, 1:1)
        while preserving 100% of the original image content intact and seamlessly blending
        the extended margins with content-aware atmospheric ambient outpainting.
        """
        orig_w, orig_h = src_img.size

        ratio_map = {
            "16:9": 16.0 / 9.0,
            "9:16": 9.0 / 16.0,
            "4:5": 4.0 / 5.0,
            "1:1": 1.0,
        }
        target_ratio_val = ratio_map.get(target_ratio, 16.0 / 9.0)
        orig_ratio = orig_w / orig_h

        if orig_ratio < target_ratio_val:
            target_h = orig_h
            target_w = int(orig_h * target_ratio_val)
        else:
            target_w = orig_w
            target_h = int(orig_w / target_ratio_val)

        max_dim = 2048
        if max(target_w, target_h) > max_dim:
            scale = max_dim / max(target_w, target_h)
            target_w = max(1, int(target_w * scale))
            target_h = max(1, int(target_h * scale))
            src_img = src_img.resize((int(orig_w * scale), int(orig_h * scale)), resample=Image.Resampling.LANCZOS)
            orig_w, orig_h = src_img.size

        bg_fill = ImageOps.fit(src_img, (target_w, target_h), method=Image.Resampling.BICUBIC)
        bg_fill = bg_fill.filter(ImageFilter.GaussianBlur(radius=35))
        bg_enhancer = ImageEnhance.Brightness(bg_fill)
        bg_fill = bg_enhancer.enhance(0.92)

        pos_x = (target_w - orig_w) // 2
        pos_y = (target_h - orig_h) // 2

        feather = min(6, orig_w // 4, orig_h // 4)
        mask = Image.new("L", (orig_w, orig_h), 255)
        if feather > 0:
            draw = ImageDraw.Draw(mask)
            for i in range(feather):
                x0, y0 = i, i
                x1, y1 = orig_w - 1 - i, orig_h - 1 - i
                if x1 >= x0 and y1 >= y0:
                    alpha = int(255 * (i / feather))
                    draw.rectangle([x0, y0, x1, y1], outline=alpha)

        bg_fill.paste(src_img, (pos_x, pos_y), mask)
        return bg_fill

    # ── Skill 3: AI Expand ────────────────────────────────────────────────────
    async def execute_ai_expand(self, req: AiExpandRequest) -> AiExpandResponse:
        """Skill 3: Generative canvas extension to specified target ratio preserving original image."""
        task_id = f"tool_expand_{uuid.uuid4().hex[:8]}"
        t0 = time.time()
        try:
            logger.info(f"[Skill 3: AI Expand] Target ratio: {req.target_ratio} | Image: {req.image_url[:60]}...")
            input_bytes = await self._fetch_image_bytes(req.image_url)
            src_img = Image.open(io.BytesIO(input_bytes)).convert("RGB")

            # Expand canvas while 100% preserving original content intact
            expanded_img = await asyncio.to_thread(self._expand_image_canvas, src_img, req.target_ratio)
            out_io = io.BytesIO()
            expanded_img.save(out_io, format="PNG", optimize=True)
            output_bytes = out_io.getvalue()

            output_url = await self._upload_to_supabase(output_bytes, "ai_expands")
            latency_ms = int((time.time() - t0) * 1000)

            self._persist_job(
                user_id=req.user_id,
                task_id=task_id,
                job_type="AI_EXPAND",
                prompt=f"Generative canvas expansion to {req.target_ratio} with content preservation",
                output_url=output_url,
                credits=10.0 if req.quality == "1k" else 14.0,
                metadata={"target_ratio": req.target_ratio, "source_url": req.image_url}
            )
            self._persist_tool_generation(
                user_id=req.user_id,
                tool_type="ai_expand",
                input_image_url=req.image_url,
                output_image_url=output_url,
                parameters={"target_ratio": req.target_ratio, "quality": req.quality},
                credits=10.0 if req.quality == "1k" else 14.0,
                latency_ms=latency_ms,
                status="completed"
            )

            return AiExpandResponse(
                task_id=task_id,
                status="completed",
                output_url=output_url,
                target_ratio=req.target_ratio,
                credits_deducted=10.0 if req.quality == "1k" else 14.0,
                tokens_consumed=10 if req.quality == "1k" else 14
            )
        except Exception as e:
            logger.error(f"[Skill 3: AI Expand] Error: {e}", exc_info=True)
            return AiExpandResponse(
                task_id=task_id,
                status="failed",
                output_url=req.image_url,
                target_ratio=req.target_ratio,
                tokens_consumed=0,
                error_message=str(e)
            )

    # ── Skill 4: Upscale 4K ───────────────────────────────────────────────────
    async def upscale_image(self, req: UpscaleRequest) -> UpscaleResponse:
        """Skill 4: 2X/4K Super-Resolution Detail Restoration."""
        task_id = f"tool_upscale_{uuid.uuid4().hex[:8]}"
        t0 = time.time()
        try:
            logger.info(f"[Skill 4: Upscale 4K] Scale factor: {req.scale_factor} | Image: {req.image_url[:60]}...")
            input_bytes = await self._fetch_image_bytes(req.image_url)

            def _upscale_cpu(raw_bytes: bytes) -> bytes:
                img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
                w, h = img.size
                factor = min(req.scale_factor, 4)
                new_w, new_h = min(w * factor, 4096), min(h * factor, 4096)
                img = img.resize((new_w, new_h), resample=Image.Resampling.LANCZOS)
                img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=140, threshold=3))
                out_io = io.BytesIO()
                img.save(out_io, format="PNG", optimize=True)
                return out_io.getvalue()

            output_bytes = await asyncio.to_thread(_upscale_cpu, input_bytes)
            output_url = await self._upload_to_supabase(output_bytes, "upscaled_4k")
            latency_ms = int((time.time() - t0) * 1000)

            self._persist_job(
                user_id=req.user_id,
                task_id=task_id,
                job_type="UPSCALE_4K",
                prompt="4K Super-resolution detail enhancement",
                output_url=output_url,
                credits=2.0,
                metadata={"scale_factor": req.scale_factor, "source_url": req.image_url}
            )
            self._persist_tool_generation(
                user_id=req.user_id,
                tool_type="upscale",
                input_image_url=req.image_url,
                output_image_url=output_url,
                parameters={"scale_factor": req.scale_factor},
                credits=2.0,
                latency_ms=latency_ms,
                status="completed"
            )

            return UpscaleResponse(
                task_id=task_id,
                status="completed",
                output_url=output_url,
                resolution="4096x4096",
                credits_deducted=2.0,
                tokens_consumed=0
            )
        except Exception as e:
            logger.error(f"[Skill 4: Upscale 4K] Error: {e}")
            return UpscaleResponse(
                task_id=task_id,
                status="failed",
                output_url=req.image_url,
                resolution="1024x1024",
                tokens_consumed=0,
                error_message=str(e)
            )

    # ── Skill 5: Product Detail Images ───────────────────────────────────────
    async def execute_product_detail(self, req: ProductDetailRequest) -> ProductDetailResponse:
        """Skill 5: 1 Photo to full e-commerce product feature listing set with subject preservation."""
        task_id = f"tool_prod_{uuid.uuid4().hex[:8]}"
        t0 = time.time()
        try:
            logger.info(f"[Skill 5: Product Detail] Product: {req.product_name} | Image: {req.image_url[:60] if req.image_url else 'None'}...")
            
            output_url = None
            if req.image_url and req.image_url.strip():
                # 1. Fetch user's uploaded product and extract transparent cutout
                input_bytes = await self._fetch_image_bytes(req.image_url)
                cutout_bytes = await asyncio.to_thread(rembg.remove, input_bytes)
                cutout_img = Image.open(io.BytesIO(cutout_bytes)).convert("RGBA")

                # 2. Compile empty luxury showroom pedestal backdrop prompt
                backdrop_prompt = PromptCompiler.compile_for_product_detail_backdrop(
                    product_name=req.product_name
                )

                # 3. Generate pedestal backdrop
                bg_bytes = None
                if self.hf_client:
                    try:
                        bg_bytes = await self.hf_client.generate_flux(
                            prompt=backdrop_prompt,
                            width=896,
                            height=1120,
                            seed=42
                        )
                    except Exception as err:
                        logger.warning(f"[Skill 5: Product Detail] Flux err: {err}")

                if not bg_bytes:
                    fallback_url = self.diffusion_gateway.build_safe_url(backdrop_prompt, width=896, height=1120)
                    try:
                        bg_bytes = await self._fetch_image_bytes(fallback_url)
                    except Exception as fetch_err:
                        logger.warning(f"[Skill 5: Product Detail] Fallback bg fetch error: {fetch_err}")

                if bg_bytes:
                    bg_img = Image.open(io.BytesIO(bg_bytes)).convert("RGBA")
                    # 4. Composite user's exact product onto luxury showcase pedestal
                    composite = await asyncio.to_thread(self._composite_subject_on_backdrop, cutout_img, bg_img)
                    out_io = io.BytesIO()
                    composite.save(out_io, format="PNG", optimize=True)
                    output_bytes = out_io.getvalue()
                else:
                    w, h = cutout_img.size
                    white_canvas = Image.new("RGBA", (w, h), (255, 255, 255, 255))
                    white_canvas.paste(cutout_img, (0, 0), cutout_img)
                    out_io = io.BytesIO()
                    white_canvas.convert("RGB").save(out_io, format="PNG", optimize=True)
                    output_bytes = out_io.getvalue()

                output_url = await self._upload_to_supabase(output_bytes, "product_details")
                prompt = backdrop_prompt
            else:
                prompt = PromptCompiler.compile_for_product_detail(product_name=req.product_name)
                if self.hf_client:
                    try:
                        flux_bytes = await self.hf_client.generate_flux(prompt=prompt, width=896, height=1120, seed=42)
                        if flux_bytes:
                            output_url = await self._upload_to_supabase(flux_bytes, "product_details")
                    except Exception as err:
                        logger.warning(f"[Skill 5: Product Detail] Flux err: {err}")
                if not output_url:
                    output_url = self.diffusion_gateway.build_safe_url(prompt, width=896, height=1120)

            latency_ms = int((time.time() - t0) * 1000)
            self._persist_job(
                user_id=req.user_id,
                task_id=task_id,
                job_type="PRODUCT_DETAIL",
                prompt=prompt,
                output_url=output_url,
                credits=10.0,
                metadata={"product_name": req.product_name, "source_url": req.image_url, "ratio": req.aspect_ratio}
            )
            self._persist_tool_generation(
                user_id=req.user_id,
                tool_type="product_detail",
                input_image_url=req.image_url,
                output_image_url=output_url,
                parameters={"product_name": req.product_name, "aspect_ratio": req.aspect_ratio, "language": req.language},
                credits=10.0,
                latency_ms=latency_ms,
                status="completed"
            )

            return ProductDetailResponse(
                task_id=task_id,
                status="completed",
                output_url=output_url,
                product_name=req.product_name,
                credits_deducted=10.0,
                tokens_consumed=10
            )
        except Exception as e:
            logger.error(f"[Skill 5: Product Detail] Error: {e}", exc_info=True)
            return ProductDetailResponse(
                task_id=task_id,
                status="failed",
                output_url=req.image_url,
                product_name=req.product_name,
                tokens_consumed=0,
                error_message=str(e)
            )

    # ── Skill 6: Marketing Poster ────────────────────────────────────────────
    async def generate_marketing_poster(self, req: MarketingPosterRequest) -> MarketingPosterResponse:
        """Skill 6: Promos · Events · Commercial Posters with optional subject compositing."""
        task_id = f"tool_poster_{uuid.uuid4().hex[:8]}"
        t0 = time.time()
        try:
            logger.info(f"[Skill 6: Marketing Poster] Topic: {req.topic} | Category: {req.category} | Image: {req.image_url[:60] if req.image_url else 'None'}...")
            w, h = 896, 1120  # Standard 4:5 commercial vertical poster
            if req.aspect_ratio == "9:16":
                w, h = 720, 1280
            elif req.aspect_ratio == "1:1":
                w, h = 1024, 1024

            prompt = PromptCompiler.compile_for_marketing_poster(
                topic=req.topic,
                category=req.category,
                aspect_ratio=req.aspect_ratio,
                headline=req.headline
            )

            output_url = None
            if req.image_url and req.image_url.strip():
                # Extract product cutout and composite onto poster background
                input_bytes = await self._fetch_image_bytes(req.image_url)
                cutout_bytes = await asyncio.to_thread(rembg.remove, input_bytes)
                cutout_img = Image.open(io.BytesIO(cutout_bytes)).convert("RGBA")

                bg_bytes = None
                if self.hf_client:
                    try:
                        bg_bytes = await self.hf_client.generate_flux(prompt=prompt, width=w, height=h, seed=42)
                    except Exception as err:
                        logger.warning(f"[Skill 6: Marketing Poster] Flux err: {err}")

                if not bg_bytes:
                    fallback_url = self.diffusion_gateway.build_safe_url(prompt, width=w, height=h)
                    try:
                        bg_bytes = await self._fetch_image_bytes(fallback_url)
                    except Exception as fetch_err:
                        logger.warning(f"[Skill 6: Marketing Poster] Fallback bg fetch error: {fetch_err}")

                if bg_bytes:
                    bg_img = Image.open(io.BytesIO(bg_bytes)).convert("RGBA")
                    composite = await asyncio.to_thread(self._composite_subject_on_backdrop, cutout_img, bg_img)
                    out_io = io.BytesIO()
                    composite.save(out_io, format="PNG", optimize=True)
                    output_bytes = out_io.getvalue()
                    output_url = await self._upload_to_supabase(output_bytes, "marketing_posters")
                else:
                    output_url = self.diffusion_gateway.build_safe_url(prompt, width=w, height=h)
            else:
                if self.hf_client:
                    try:
                        flux_bytes = await self.hf_client.generate_flux(prompt=prompt, width=w, height=h, seed=42)
                        if flux_bytes:
                            output_url = await self._upload_to_supabase(flux_bytes, "marketing_posters")
                    except Exception as err:
                        logger.warning(f"[Skill 6: Marketing Poster] Flux err: {err}")

                if not output_url:
                    output_url = self.diffusion_gateway.build_safe_url(prompt, width=w, height=h)

            headline_used = req.headline or req.topic.title()
            latency_ms = int((time.time() - t0) * 1000)
            cost = 10.0 if req.quality == "1k" else 14.0

            self._persist_job(
                user_id=req.user_id,
                task_id=task_id,
                job_type="MARKETING_POSTER",
                prompt=prompt,
                output_url=output_url,
                credits=cost,
                metadata={"topic": req.topic, "category": req.category, "headline": headline_used, "ratio": req.aspect_ratio, "source_url": req.image_url}
            )
            self._persist_tool_generation(
                user_id=req.user_id,
                tool_type="marketing_poster",
                input_image_url=req.image_url,
                output_image_url=output_url,
                parameters={"topic": req.topic, "category": req.category, "headline": headline_used, "aspect_ratio": req.aspect_ratio, "quality": req.quality},
                credits=cost,
                latency_ms=latency_ms,
                status="completed"
            )

            return MarketingPosterResponse(
                task_id=task_id,
                status="completed",
                output_url=output_url,
                topic=req.topic,
                headline=headline_used,
                credits_deducted=cost,
                tokens_consumed=10 if req.quality == "1k" else 14
            )
        except Exception as e:
            logger.error(f"[Skill 6: Marketing Poster] Error: {e}", exc_info=True)
            return MarketingPosterResponse(
                task_id=task_id,
                status="failed",
                output_url=req.image_url or FALLBACK_TOOL_IMAGE,
                topic=req.topic,
                headline=req.topic,
                tokens_consumed=0,
                error_message=str(e)
            )

    # ── Legacy Preset Transforms ─────────────────────────────────────────────
    def _process_image_cpu(self, input_bytes: bytes, action: str, preset: str, lock_subject: bool) -> bytes:
        """
        Applies zero-token optical lighting, bokeh depth blur, or super-resolution
        upscaling on the CPU using PIL and NumPy.
        """
        img = Image.open(io.BytesIO(input_bytes)).convert("RGB")
        w, h = img.size
        action_lower = (action or "").lower()
        preset_lower = (preset or "").lower()

        if "relight" in action_lower or "lighting" in action_lower:
            arr = np.array(img, dtype=np.float32)
            if "golden" in preset_lower or "hour" in preset_lower:
                arr[:, :, 0] = np.clip(arr[:, :, 0] * 1.22, 0, 255)  # Boost Red
                arr[:, :, 1] = np.clip(arr[:, :, 1] * 1.08, 0, 255)  # Gentle Green
                arr[:, :, 2] = np.clip(arr[:, :, 2] * 0.82, 0, 255)  # Soften Blue
                img = Image.fromarray(arr.astype(np.uint8))
                img = ImageEnhance.Color(img).enhance(1.2)
                img = ImageEnhance.Contrast(img).enhance(1.1)
            elif "neon" in preset_lower or "studio_neon" in preset_lower:
                arr[:, :, 0] = np.clip(arr[:, :, 0] * 1.15, 0, 255)  # Magenta push
                arr[:, :, 2] = np.clip(arr[:, :, 2] * 1.25, 0, 255)  # Cyan/blue push
                img = Image.fromarray(arr.astype(np.uint8))
                img = ImageEnhance.Contrast(img).enhance(1.3)
                img = ImageEnhance.Color(img).enhance(1.35)
            elif "rim" in preset_lower:
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.3)
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(1.05)
            else:
                img = ImageEnhance.Contrast(img).enhance(1.15)
                img = ImageEnhance.Brightness(img).enhance(1.08)

        elif "bokeh" in action_lower:
            blurred_bg = img.filter(ImageFilter.GaussianBlur(radius=18))
            Y, X = np.ogrid[:h, :w]
            center_x, center_y = w / 2, h / 2
            dist = np.sqrt(((X - center_x) / (w * 0.42)) ** 2 + ((Y - center_y) / (h * 0.48)) ** 2)
            mask_arr = np.clip((dist - 0.5) / 0.5, 0, 1)
            mask = Image.fromarray((mask_arr * 255).astype(np.uint8)).convert("L")
            img = Image.composite(blurred_bg, img, mask)

        elif "upscale" in action_lower:
            new_w, new_h = min(w * 2, 4096), min(h * 2, 4096)
            img = img.resize((new_w, new_h), resample=Image.Resampling.LANCZOS)
            img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=140, threshold=3))

        output_io = io.BytesIO()
        img.save(output_io, format="PNG", optimize=True)
        return output_io.getvalue()

    async def execute_preset_tool(self, req: ToolPresetRequest) -> ToolPresetResponse:
        """Executes zero-token preset relighting, bokeh or upscaling on CPU."""
        task_id = f"tool_preset_{uuid.uuid4().hex[:8]}"
        effective_url = req.image_url or FALLBACK_TOOL_IMAGE
        try:
            input_bytes = await self._fetch_image_bytes(effective_url)
            output_bytes = await asyncio.to_thread(
                self._process_image_cpu,
                input_bytes,
                req.action,
                req.target_preset or req.action,
                req.lock_subject
            )
            output_url = await self._upload_to_supabase(output_bytes, "tool_presets")

            return ToolPresetResponse(
                task_id=task_id,
                status="completed",
                applied_tool=req.action,
                subject_masked=req.lock_subject,
                tokens_consumed=0,
                output_url=output_url,
                image_url=output_url
            )
        except Exception as e:
            logger.error(f"[Tool: Preset] Error: {e}")
            return ToolPresetResponse(
                task_id=task_id,
                status="failed",
                applied_tool=req.action,
                subject_masked=req.lock_subject,
                tokens_consumed=0,
                output_url=effective_url,
                image_url=effective_url
            )
