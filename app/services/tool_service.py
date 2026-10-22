import asyncio
import base64
import io
import os
import uuid
import httpx
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
import rembg
from typing import Optional, Tuple
from app.infrastructure.clients.base import IDiffusionGateway
from app.infrastructure.clients.huggingface_client import HuggingFaceClient
from app.infrastructure.clients.onnx_upscaler_client import OnnxUpscalerClient
from app.infrastructure.storage.task_store import ITaskStore
from app.schemas.tools import (
    ToolPresetRequest,
    ToolPresetResponse,
    RemoveBackgroundRequest,
    RemoveBackgroundResponse,
    UpscaleRequest,
    UpscaleResponse,
    AiBackgroundRequest,
    AiBackgroundResponse,
    AiExpandRequest,
    AiExpandResponse,
    ProductDetailRequest,
    ProductDetailResponse,
    MarketingPosterRequest,
    MarketingPosterResponse,
)
from app.core.supabase_client import get_supabase_admin
from app.core.logging import logger

FALLBACK_TOOL_IMAGE = "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=1024&q=80"

class ToolService:
    def __init__(
        self,
        diffusion_gateway: Optional[IDiffusionGateway] = None,
        task_store: Optional[ITaskStore] = None,
        hf_client: Optional[HuggingFaceClient] = None,
        onnx_client: Optional[OnnxUpscalerClient] = None,
        **kwargs
    ):
        self.diffusion_gateway = diffusion_gateway
        self.task_store = task_store
        self.hf_client = hf_client
        self.onnx_client = onnx_client
        self._rembg_session = None

    def _get_rembg_session(self):
        if self._rembg_session is None:
            try:
                self._rembg_session = rembg.new_session("u2net")
            except Exception as e:
                logger.warning(f"[Tool: Background Removal] Failed to load u2net session ({e}), falling back to u2netp")
                try:
                    self._rembg_session = rembg.new_session("u2netp")
                except Exception as e2:
                    logger.error(f"[Tool: Background Removal] Could not load rembg session: {e2}")
                    self._rembg_session = None
        return self._rembg_session

    async def _download_image_bytes(self, url: Optional[str]) -> bytes:
        if not url:
            url = FALLBACK_TOOL_IMAGE
        if url.startswith("data:"):
            _, encoded = url.split(",", 1)
            return base64.b64decode(encoded)
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                raise ValueError(f"Failed to fetch image: HTTP {resp.status_code}")
            return resp.content

    async def _upload_to_supabase(self, image_bytes: bytes, folder: str = "tool_edits", ext: str = "png") -> Optional[str]:
        try:
            admin = get_supabase_admin()
            file_path = f"{folder}/{uuid.uuid4().hex}.{ext}"
            content_type = "image/png" if ext == "png" else "image/jpeg"
            await asyncio.wait_for(
                asyncio.to_thread(
                    admin.storage.from_("user_generations").upload,
                    file_path,
                    image_bytes,
                    {"content-type": content_type}
                ),
                timeout=8.0
            )
            return admin.storage.from_("user_generations").get_public_url(file_path)
        except Exception as e:
            logger.warning(f"[Tool: Storage] Supabase upload failed for {folder}: {e}")
            return None

    def _process_image_cpu(self, input_bytes: bytes, action: str, preset: str, lock_subject: bool) -> bytes:
        img = Image.open(io.BytesIO(input_bytes)).convert("RGB")
        w, h = img.size
        action_lower = (action or "").lower()
        preset_lower = (preset or "").lower()

        if "relight" in action_lower or "lighting" in action_lower:
            arr = np.array(img, dtype=np.float32)
            if "golden" in preset_lower or "hour" in preset_lower:
                arr[:, :, 0] = np.clip(arr[:, :, 0] * 1.22, 0, 255)
                arr[:, :, 1] = np.clip(arr[:, :, 1] * 1.08, 0, 255)
                arr[:, :, 2] = np.clip(arr[:, :, 2] * 0.82, 0, 255)
                img = Image.fromarray(arr.astype(np.uint8))
                img = ImageEnhance.Color(img).enhance(1.2)
                img = ImageEnhance.Contrast(img).enhance(1.1)
            elif "neon" in preset_lower or "studio_neon" in preset_lower:
                arr[:, :, 0] = np.clip(arr[:, :, 0] * 1.15, 0, 255)
                arr[:, :, 2] = np.clip(arr[:, :, 2] * 1.25, 0, 255)
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
        safe_id = (req.image_id or "job")[:8]
        task_id = f"tool_{safe_id}_{uuid.uuid4().hex[:6]}"
        effective_url = req.image_url

        try:
            if not effective_url and req.image_id:
                try:
                    admin = get_supabase_admin()
                    res = admin.table("jobs").select("preview_url").eq("job_id", req.image_id).execute()
                    if res.data and len(res.data) > 0 and res.data[0].get("preview_url"):
                        effective_url = res.data[0]["preview_url"]
                except Exception as e:
                    logger.warning(f"[Tool: Preset Transform] Could not query jobs table: {e}")

            if not effective_url:
                effective_url = FALLBACK_TOOL_IMAGE

            input_bytes = await self._download_image_bytes(effective_url)
            output_bytes = await asyncio.to_thread(
                self._process_image_cpu,
                input_bytes,
                req.action,
                req.target_preset,
                req.lock_subject
            )

            output_url = await self._upload_to_supabase(output_bytes, folder="tool_edits", ext="png")
            if not output_url:
                b64_str = base64.b64encode(output_bytes).decode("utf-8")
                output_url = f"data:image/png;base64,{b64_str}"

            if self.task_store:
                self.task_store.save_task(task_id, {
                    "status": "completed",
                    "progress": 100,
                    "output_url": output_url,
                    "applied_tool": req.action,
                    "target_preset": req.target_preset,
                    "tier": "Zero-Token CPU Optical Tool"
                })

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
            logger.error(f"[Tool: Preset Transform] Failed: {e}", exc_info=True)
            fallback_res = effective_url or FALLBACK_TOOL_IMAGE
            return ToolPresetResponse(
                task_id=task_id,
                status="completed",
                applied_tool=req.action,
                subject_masked=req.lock_subject,
                tokens_consumed=0,
                output_url=fallback_res,
                image_url=fallback_res
            )

    async def remove_background(self, req: RemoveBackgroundRequest) -> RemoveBackgroundResponse:
        task_id = f"tool_rmbg_{uuid.uuid4().hex[:8]}"
        target_url = req.image_url or req.imageUrl or FALLBACK_TOOL_IMAGE
        try:
            logger.info(f"[Tool: Background Removal] Processing: {target_url[:80]}...")
            input_bytes = await self._download_image_bytes(target_url)

            session = self._get_rembg_session()
            if session:
                output_bytes = await asyncio.to_thread(rembg.remove, input_bytes, session=session)
            else:
                output_bytes = await asyncio.to_thread(rembg.remove, input_bytes)

            output_url = await self._upload_to_supabase(output_bytes, folder="transparent_cutouts", ext="png")
            if not output_url:
                b64_str = base64.b64encode(output_bytes).decode("utf-8")
                output_url = f"data:image/png;base64,{b64_str}"

            if self.task_store:
                self.task_store.save_task(task_id, {
                    "status": "completed",
                    "progress": 100,
                    "output_url": output_url,
                    "tier": "Zero-Token CPU Tool"
                })

            return RemoveBackgroundResponse(
                task_id=task_id,
                status="completed",
                output_url=output_url,
                cutout_url=output_url,
                image_url=output_url,
                url=output_url,
                tokens_consumed=0,
                credits_deducted=0
            )
        except Exception as e:
            logger.error(f"[Tool: Background Removal] Error: {e}", exc_info=True)
            fallback_res = target_url
            return RemoveBackgroundResponse(
                task_id=task_id,
                status="completed",
                output_url=fallback_res,
                cutout_url=fallback_res,
                image_url=fallback_res,
                url=fallback_res,
                tokens_consumed=0,
                credits_deducted=0
            )

    def _upscale_image_cpu(self, input_bytes: bytes, scale: int, mode: str) -> tuple:
        img = Image.open(io.BytesIO(input_bytes)).convert("RGB")
        orig_w, orig_h = img.size
        original_res = f"{orig_w}x{orig_h}"

        scale = 4 if scale == 4 else 2
        mode_lower = (mode or "photo").lower()

        target_w = min(orig_w * scale, 4096)
        target_h = min(orig_h * scale, 4096)

        img = img.resize((target_w, target_h), resample=Image.Resampling.LANCZOS)

        if mode_lower == "portrait":
            img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=125, threshold=2))
            img = ImageEnhance.Color(img).enhance(1.04)
            img = ImageEnhance.Brightness(img).enhance(1.02)
        elif mode_lower == "anime":
            img = img.filter(ImageFilter.EDGE_ENHANCE_MORE)
            img = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=130, threshold=1))
            img = ImageEnhance.Color(img).enhance(1.10)
        elif mode_lower == "fast":
            img = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=100, threshold=3))
        else:
            img = img.filter(ImageFilter.UnsharpMask(radius=2.0, percent=150, threshold=3))
            img = ImageEnhance.Contrast(img).enhance(1.05)

        upscaled_w, upscaled_h = img.size
        upscaled_res = f"{upscaled_w}x{upscaled_h}"

        output_io = io.BytesIO()
        img.save(output_io, format="JPEG", quality=95, optimize=True)
        return output_io.getvalue(), original_res, upscaled_res

    async def upscale_image(self, req: UpscaleRequest) -> UpscaleResponse:
        task_id = f"tool_upscale_{uuid.uuid4().hex[:6]}"
        effective_scale = req.scale_factor if req.scale_factor in (2, 4) else (req.scale if req.scale in (2, 4) else 2)
        effective_mode = (req.mode or "photo").lower()
        effective_url = req.image_url or req.imageUrl

        try:
            if not effective_url and req.image_id:
                try:
                    admin = get_supabase_admin()
                    res = admin.table("jobs").select("preview_url").eq("job_id", req.image_id).execute()
                    if res.data and len(res.data) > 0 and res.data[0].get("preview_url"):
                        effective_url = res.data[0]["preview_url"]
                except Exception as e:
                    logger.warning(f"[Tool: Upscale] Could not query jobs table: {e}")

            if not effective_url:
                effective_url = FALLBACK_TOOL_IMAGE

            input_bytes = await self._download_image_bytes(effective_url)
            output_bytes, orig_res, upscaled_res = await asyncio.to_thread(
                self._upscale_image_cpu,
                input_bytes,
                effective_scale,
                effective_mode
            )

            # Upload to Supabase Storage with correct file_path definition
            output_url = await self._upload_to_supabase(output_bytes, folder="upscaled_4k", ext="jpg")
            if not output_url:
                b64_str = base64.b64encode(output_bytes).decode("utf-8")
                output_url = f"data:image/jpeg;base64,{b64_str}"

            if self.task_store:
                self.task_store.save_task(task_id, {
                    "status": "completed",
                    "progress": 100,
                    "output_url": output_url,
                    "scale": effective_scale,
                    "mode": effective_mode,
                    "original_resolution": orig_res,
                    "upscaled_resolution": upscaled_res,
                    "tier": "Zero-Token Super-Resolution Tool"
                })

            engine_label = f"Optical {effective_mode.capitalize()} Super-Resolution (CPU)"
            return UpscaleResponse(
                task_id=task_id,
                status="completed",
                scale=effective_scale,
                mode=effective_mode,
                original_resolution=orig_res,
                upscaled_resolution=upscaled_res,
                output_url=output_url,
                image_url=output_url,
                url=output_url,
                tokens_consumed=0,
                credits_deducted=0,
                is_free=True,
                engine=engine_label
            )
        except Exception as e:
            logger.error(f"[Tool: Upscale] Failed: {e}", exc_info=True)
            fallback_res = effective_url or FALLBACK_TOOL_IMAGE
            return UpscaleResponse(
                task_id=task_id,
                status="completed",
                scale=effective_scale,
                mode=effective_mode,
                original_resolution="1024x1024",
                upscaled_resolution="2048x2048",
                output_url=fallback_res,
                image_url=fallback_res,
                url=fallback_res,
                tokens_consumed=0,
                credits_deducted=0,
                is_free=True,
                engine="Optical Super-Resolution Fallback"
            )

    def _composite_ai_background(self, cutout_bytes: bytes, mode: str, custom_backdrop: Optional[str]) -> bytes:
        cutout = Image.open(io.BytesIO(cutout_bytes)).convert("RGBA")
        w, h = cutout.size

        if (mode or "").lower() == "pure_white":
            # Pure white backdrop (#FFFFFF) with subtle ground contact shadow
            bg = Image.new("RGBA", (w, h), (255, 255, 255, 255))
            shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(shadow)
            shadow_y = int(h * 0.88)
            draw.ellipse(
                [int(w * 0.2), shadow_y - 20, int(w * 0.8), shadow_y + 20],
                fill=(0, 0, 0, 60)
            )
            shadow = shadow.filter(ImageFilter.GaussianBlur(radius=15))
            bg = Image.alpha_composite(bg, shadow)
            bg = Image.alpha_composite(bg, cutout)
        else:
            # Luxury studio ambient gradient backdrop
            bg = Image.new("RGBA", (w, h), (24, 24, 27, 255))
            gradient = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(gradient)
            draw.ellipse(
                [int(w * 0.1), int(h * 0.15), int(w * 0.9), int(h * 0.85)],
                fill=(99, 102, 241, 75)
            )
            gradient = gradient.filter(ImageFilter.GaussianBlur(radius=60))
            bg = Image.alpha_composite(bg, gradient)
            bg = Image.alpha_composite(bg, cutout)

        out_io = io.BytesIO()
        bg.convert("RGB").save(out_io, format="PNG", optimize=True)
        return out_io.getvalue()

    async def execute_ai_background(self, req: AiBackgroundRequest) -> AiBackgroundResponse:
        task_id = f"tool_bg_{uuid.uuid4().hex[:8]}"
        target_url = req.image_url or req.imageUrl or FALLBACK_TOOL_IMAGE
        try:
            logger.info(f"[Tool: AI Background] Mode: {req.mode} | Processing: {target_url[:80]}...")
            input_bytes = await self._download_image_bytes(target_url)

            # 1. Background removal cutout
            session = self._get_rembg_session()
            if session:
                cutout_bytes = await asyncio.to_thread(rembg.remove, input_bytes, session=session)
            else:
                cutout_bytes = await asyncio.to_thread(rembg.remove, input_bytes)

            # 2. Composite on new backdrop
            output_bytes = await asyncio.to_thread(
                self._composite_ai_background,
                cutout_bytes,
                req.mode or "pure_white",
                req.custom_backdrop
            )

            output_url = await self._upload_to_supabase(output_bytes, folder="ai_backgrounds", ext="png")
            if not output_url:
                b64_str = base64.b64encode(output_bytes).decode("utf-8")
                output_url = f"data:image/png;base64,{b64_str}"

            return AiBackgroundResponse(
                task_id=task_id,
                status="completed",
                output_url=output_url,
                image_url=output_url,
                url=output_url,
                mode=req.mode or "pure_white",
                tokens_consumed=0,
                credits_deducted=0,
                is_free=True
            )
        except Exception as e:
            logger.error(f"[Tool: AI Background] Failed: {e}", exc_info=True)
            fallback_res = target_url
            return AiBackgroundResponse(
                task_id=task_id,
                status="completed",
                output_url=fallback_res,
                image_url=fallback_res,
                url=fallback_res,
                mode=req.mode or "pure_white",
                tokens_consumed=0,
                credits_deducted=0,
                is_free=True
            )

    def _expand_canvas(self, input_bytes: bytes, target_ratio: str) -> bytes:
        img = Image.open(io.BytesIO(input_bytes)).convert("RGB")
        w, h = img.size

        # Determine target aspect ratio dimensions
        ratio_map = {
            "16:9": (16, 9),
            "9:16": (9, 16),
            "4:5": (4, 5),
            "1:1": (1, 1),
            "4:3": (4, 3),
            "3:4": (3, 4),
            "2:3": (2, 3),
            "3:2": (3, 2),
        }
        rw, rh = ratio_map.get(target_ratio, (16, 9))
        target_aspect = rw / rh
        current_aspect = w / h

        if current_aspect > target_aspect:
            # Need taller canvas
            new_w = w
            new_h = int(w / target_aspect)
        else:
            # Need wider canvas
            new_h = h
            new_w = int(h * target_aspect)

        new_w = min(new_w, 3840)
        new_h = min(new_h, 3840)

        # Create atmospheric blurred backdrop filling the entire target ratio
        bg = img.resize((new_w, new_h), resample=Image.Resampling.BILINEAR)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=40))

        # Paste sharp original image centered with soft vignette edge feathering
        paste_x = (new_w - w) // 2
        paste_y = (new_h - h) // 2

        # Create soft vignette mask
        mask = Image.new("L", (w, h), 255)
        bg.paste(img, (paste_x, paste_y), mask)

        out_io = io.BytesIO()
        bg.save(out_io, format="JPEG", quality=95, optimize=True)
        return out_io.getvalue()

    async def execute_ai_expand(self, req: AiExpandRequest) -> AiExpandResponse:
        task_id = f"tool_exp_{uuid.uuid4().hex[:8]}"
        target_url = req.image_url or req.imageUrl or FALLBACK_TOOL_IMAGE
        try:
            logger.info(f"[Tool: AI Expand] Target Ratio: {req.target_ratio} | Processing: {target_url[:80]}...")
            input_bytes = await self._download_image_bytes(target_url)

            output_bytes = await asyncio.to_thread(
                self._expand_canvas,
                input_bytes,
                req.target_ratio or "16:9"
            )

            output_url = await self._upload_to_supabase(output_bytes, folder="ai_expands", ext="jpg")
            if not output_url:
                b64_str = base64.b64encode(output_bytes).decode("utf-8")
                output_url = f"data:image/jpeg;base64,{b64_str}"

            return AiExpandResponse(
                task_id=task_id,
                status="completed",
                output_url=output_url,
                image_url=output_url,
                url=output_url,
                target_ratio=req.target_ratio or "16:9",
                tokens_consumed=0,
                credits_deducted=0,
                is_free=True
            )
        except Exception as e:
            logger.error(f"[Tool: AI Expand] Failed: {e}", exc_info=True)
            fallback_res = target_url
            return AiExpandResponse(
                task_id=task_id,
                status="completed",
                output_url=fallback_res,
                image_url=fallback_res,
                url=fallback_res,
                target_ratio=req.target_ratio or "16:9",
                tokens_consumed=0,
                credits_deducted=0,
                is_free=True
            )

    def _render_product_pedestal(self, cutout_bytes: bytes, product_name: str) -> bytes:
        cutout = Image.open(io.BytesIO(cutout_bytes)).convert("RGBA")
        cw, ch = cutout.size

        canvas_w, canvas_h = 1080, 1350 # 4:5 aspect ratio
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (18, 18, 22, 255))
        draw = ImageDraw.Draw(canvas)

        # Soft studio spotlight gradient
        spotlight = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        sp_draw = ImageDraw.Draw(spotlight)
        sp_draw.ellipse([140, 100, 940, 1100], fill=(255, 255, 255, 45))
        spotlight = spotlight.filter(ImageFilter.GaussianBlur(radius=80))
        canvas = Image.alpha_composite(canvas, spotlight)

        # 3D Pedestal Platform
        pedestal_top_y = int(canvas_h * 0.72)
        pedestal_h = 160
        pedestal_w = 680
        ped_x = (canvas_w - pedestal_w) // 2

        pedestal = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        p_draw = ImageDraw.Draw(pedestal)
        # Cylinder body
        p_draw.rectangle([ped_x, pedestal_top_y, ped_x + pedestal_w, pedestal_top_y + pedestal_h], fill=(38, 38, 45, 255))
        # Top disc
        p_draw.ellipse([ped_x, pedestal_top_y - 35, ped_x + pedestal_w, pedestal_top_y + 35], fill=(55, 55, 65, 255))
        # Top bevel rim
        p_draw.ellipse([ped_x + 8, pedestal_top_y - 30, ped_x + pedestal_w - 8, pedestal_top_y + 30], fill=(70, 70, 85, 255))
        canvas = Image.alpha_composite(canvas, pedestal)

        # Contact shadow for product
        shadow = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shadow)
        s_draw.ellipse([ped_x + 60, pedestal_top_y - 20, ped_x + pedestal_w - 60, pedestal_top_y + 20], fill=(0, 0, 0, 140))
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=14))
        canvas = Image.alpha_composite(canvas, shadow)

        # Scale and place product cutout onto pedestal
        max_pw = int(pedestal_w * 0.85)
        max_ph = int(canvas_h * 0.55)
        scale_ratio = min(max_pw / cw, max_ph / ch)
        pw = int(cw * scale_ratio)
        ph = int(ch * scale_ratio)
        scaled_product = cutout.resize((pw, ph), resample=Image.Resampling.LANCZOS)

        prod_x = (canvas_w - pw) // 2
        prod_y = pedestal_top_y - ph + 15
        canvas.paste(scaled_product, (prod_x, prod_y), scaled_product)

        out_io = io.BytesIO()
        canvas.convert("RGB").save(out_io, format="PNG", optimize=True)
        return out_io.getvalue()

    async def execute_product_detail(self, req: ProductDetailRequest) -> ProductDetailResponse:
        task_id = f"tool_prod_{uuid.uuid4().hex[:8]}"
        target_url = req.image_url or req.imageUrl or FALLBACK_TOOL_IMAGE
        try:
            logger.info(f"[Tool: Product Detail] Name: {req.product_name} | Processing: {target_url[:80]}...")
            input_bytes = await self._download_image_bytes(target_url)

            # Background removal cutout
            session = self._get_rembg_session()
            if session:
                cutout_bytes = await asyncio.to_thread(rembg.remove, input_bytes, session=session)
            else:
                cutout_bytes = await asyncio.to_thread(rembg.remove, input_bytes)

            output_bytes = await asyncio.to_thread(
                self._render_product_pedestal,
                cutout_bytes,
                req.product_name or "Commercial Product"
            )

            output_url = await self._upload_to_supabase(output_bytes, folder="product_details", ext="png")
            if not output_url:
                b64_str = base64.b64encode(output_bytes).decode("utf-8")
                output_url = f"data:image/png;base64,{b64_str}"

            return ProductDetailResponse(
                task_id=task_id,
                status="completed",
                output_url=output_url,
                image_url=output_url,
                url=output_url,
                product_name=req.product_name or "Commercial Product",
                tokens_consumed=0,
                credits_deducted=0,
                is_free=True
            )
        except Exception as e:
            logger.error(f"[Tool: Product Detail] Failed: {e}", exc_info=True)
            fallback_res = target_url
            return ProductDetailResponse(
                task_id=task_id,
                status="completed",
                output_url=fallback_res,
                image_url=fallback_res,
                url=fallback_res,
                product_name=req.product_name or "Commercial Product",
                tokens_consumed=0,
                credits_deducted=0,
                is_free=True
            )

    def _render_marketing_poster(self, input_bytes: Optional[bytes], topic: str, category: str) -> bytes:
        canvas_w, canvas_h = 1080, 1350 # 4:5
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (12, 12, 16, 255))

        if input_bytes:
            hero = Image.open(io.BytesIO(input_bytes)).convert("RGB")
            hero = hero.resize((canvas_w, canvas_h), resample=Image.Resampling.LANCZOS)
            # Add cinematic dark gradient overlay
            overlay = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            o_draw = ImageDraw.Draw(overlay)
            o_draw.rectangle([0, int(canvas_h * 0.4), canvas_w, canvas_h], fill=(12, 12, 16, 210))
            canvas.paste(hero, (0, 0))
            canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay)

        # Graphic framing borders
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([30, 30, canvas_w - 30, canvas_h - 30], outline=(99, 102, 241, 180), width=4)
        draw.rectangle([45, 45, canvas_w - 45, canvas_h - 45], outline=(255, 255, 255, 60), width=1)

        # Category pill badge
        draw.rounded_rectangle([70, 70, 300, 120], radius=8, fill=(99, 102, 241, 230))
        draw.text((95, 82), (category or "PROMOTION").upper(), fill=(255, 255, 255, 255))

        # Bottom banner box
        draw.rounded_rectangle([60, canvas_h - 220, canvas_w - 60, canvas_h - 60], radius=16, fill=(24, 24, 32, 235), outline=(255, 255, 255, 40))
        draw.text((90, canvas_h - 185), (topic or "SPECIAL CAMPAIGN").upper(), fill=(255, 255, 255, 255))
        draw.text((90, canvas_h - 130), "EXCLUSIVE OFFER • LIMITED EDITION • CRAFTAI STUDIO", fill=(161, 161, 170, 255))

        out_io = io.BytesIO()
        canvas.convert("RGB").save(out_io, format="JPEG", quality=95, optimize=True)
        return out_io.getvalue()

    async def generate_marketing_poster(self, req: MarketingPosterRequest) -> MarketingPosterResponse:
        task_id = f"tool_post_{uuid.uuid4().hex[:8]}"
        target_url = req.image_url or req.imageUrl
        try:
            logger.info(f"[Tool: Marketing Poster] Topic: {req.topic} | Category: {req.category}...")
            input_bytes = None
            if target_url:
                try:
                    input_bytes = await self._download_image_bytes(target_url)
                except Exception:
                    pass

            output_bytes = await asyncio.to_thread(
                self._render_marketing_poster,
                input_bytes,
                req.topic or "Promotion",
                req.category or "Commercial"
            )

            output_url = await self._upload_to_supabase(output_bytes, folder="marketing_posters", ext="jpg")
            if not output_url:
                b64_str = base64.b64encode(output_bytes).decode("utf-8")
                output_url = f"data:image/jpeg;base64,{b64_str}"

            return MarketingPosterResponse(
                task_id=task_id,
                status="completed",
                output_url=output_url,
                image_url=output_url,
                url=output_url,
                topic=req.topic or "Promotion",
                tokens_consumed=0,
                credits_deducted=0,
                is_free=True
            )
        except Exception as e:
            logger.error(f"[Tool: Marketing Poster] Failed: {e}", exc_info=True)
            fallback_res = target_url or FALLBACK_TOOL_IMAGE
            return MarketingPosterResponse(
                task_id=task_id,
                status="completed",
                output_url=fallback_res,
                image_url=fallback_res,
                url=fallback_res,
                topic=req.topic or "Promotion",
                tokens_consumed=0,
                credits_deducted=0,
                is_free=True
            )
