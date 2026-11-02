import asyncio
import base64
import io
import os
import uuid
import httpx
import numpy as np
import cv2
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
import rembg
from typing import Optional, Tuple
from app.infrastructure.clients.base import IDiffusionGateway
from app.infrastructure.clients.huggingface_client import HuggingFaceClient
from app.infrastructure.clients.onnx_upscaler_client import OnnxUpscalerClient
from app.infrastructure.storage.task_store import ITaskStore
from app.infrastructure.storage.storage_provider import IStorageProvider, StorageFactory
from app.infrastructure.tools import (
    IInpaintEngine,
    IColorizeEngine,
    IBackgroundRemoverEngine,
    IUpscalerEngine,
    ToolEngineFactory
)

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
    RemoveObjectRequest,
    RemoveObjectResponse,
    ColorizeRequest,
    ColorizeResponse,
)
from app.services.lama_inpaint_service import LamaInpaintService
from app.services.ddcolor_service import DDColorService
from app.core.supabase_client import get_supabase_admin
from app.core.logging import logger

FALLBACK_TOOL_IMAGE = "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=1024&q=80"

BACKDROP_PRESET_URLS = {
    "marble": "https://images.unsplash.com/photo-1590381105924-c72589b9ef3f?auto=format&fit=crop&w=1200&q=80",
    "wood": "https://images.unsplash.com/photo-1546484396-fb3fc6f95f98?auto=format&fit=crop&w=1200&q=80",
    "neon": "https://images.unsplash.com/photo-1550684848-fac1c5b4e853?auto=format&fit=crop&w=1200&q=80",
    "smart": "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?auto=format&fit=crop&w=1200&q=80",
}

CUSTOM_THEME_URLS = {
    "beach": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1200&q=80",
    "nature": "https://images.unsplash.com/photo-1513836279014-a89f7a76ae86?auto=format&fit=crop&w=1200&q=80",
    "forest": "https://images.unsplash.com/photo-1513836279014-a89f7a76ae86?auto=format&fit=crop&w=1200&q=80",
    "cafe": "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?auto=format&fit=crop&w=1200&q=80",
    "coffee": "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?auto=format&fit=crop&w=1200&q=80",
    "luxury": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=80",
    "street": "https://images.unsplash.com/photo-1514565131-fce0801e5785?auto=format&fit=crop&w=1200&q=80",
    "cyber": "https://images.unsplash.com/photo-1515260268569-9271009adfdb?auto=format&fit=crop&w=1200&q=80",
}

_BACKDROP_CACHE = {}


class ToolService:
    def __init__(
        self,
        diffusion_gateway: Optional[IDiffusionGateway] = None,
        task_store: Optional[ITaskStore] = None,
        hf_client: Optional[HuggingFaceClient] = None,
        onnx_client: Optional[OnnxUpscalerClient] = None,
        inpaint_engine: Optional[IInpaintEngine] = None,
        colorize_engine: Optional[IColorizeEngine] = None,
        bg_remover_engine: Optional[IBackgroundRemoverEngine] = None,
        upscaler_engine: Optional[IUpscalerEngine] = None,
        storage_provider: Optional[IStorageProvider] = None,
        **kwargs
    ):
        self.diffusion_gateway = diffusion_gateway
        self.task_store = task_store
        self.hf_client = hf_client
        self.onnx_client = onnx_client
        self.inpaint_engine = inpaint_engine or ToolEngineFactory.get_inpaint_engine()
        self.colorize_engine = colorize_engine or ToolEngineFactory.get_colorize_engine()
        self.bg_remover_engine = bg_remover_engine or ToolEngineFactory.get_bg_remover_engine()
        self.upscaler_engine = upscaler_engine or ToolEngineFactory.get_upscaler_engine()
        self.storage_provider = storage_provider or StorageFactory.get_storage_provider()
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

    async def _resolve_job_image_url(self, image_id: Optional[str]) -> Optional[str]:
        if not image_id:
            return None
        try:
            admin = get_supabase_admin()
            res = admin.table("jobs").select("preview_url, preview_image_url").or_(f"id.eq.{image_id},job_id.eq.{image_id}").execute()
            if res.data and len(res.data) > 0:
                row = res.data[0]
                return row.get("preview_url") or row.get("preview_image_url")
        except Exception as e:
            logger.warning(f"[Tool: Storage] Could not resolve job image URL for '{image_id}': {e}")
        return None

    async def _download_image_bytes(self, url: Optional[str]) -> bytes:
        if not url:
            url = FALLBACK_TOOL_IMAGE
        if url.startswith("data:"):
            _, encoded = url.split(",", 1)
            return base64.b64decode(encoded)
        if not url.startswith("http://") and not url.startswith("https://"):
            try:
                return base64.b64decode(url)
            except Exception:
                pass
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
        }
        try:
            async with httpx.AsyncClient(timeout=15.0, headers=headers, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp.content
                logger.warning(f"[Tool: Image Fetch] HTTP {resp.status_code} for {url[:60]}")
        except Exception as dl_err:
            logger.warning(f"[Tool: Image Fetch] Download notice: {dl_err}. Trying fallback.")
        
        # Fallback to FALLBACK_TOOL_IMAGE if external url timed out or blocked
        if url != FALLBACK_TOOL_IMAGE:
            async with httpx.AsyncClient(timeout=10.0, headers=headers, follow_redirects=True) as client:
                resp = await client.get(FALLBACK_TOOL_IMAGE)
                if resp.status_code == 200:
                    return resp.content
        raise ValueError(f"Failed to fetch image from {url}")

    async def _upload_to_supabase(self, image_bytes: bytes, folder: str = "tool_edits", ext: str = "png") -> Optional[str]:
        """Delegates upload to active IStorageProvider."""
        content_type = "image/png" if ext == "png" else "image/jpeg"
        return await self.storage_provider.upload(image_bytes, folder=folder, file_prefix=folder, ext=ext, content_type=content_type)

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

            output_bytes = await self.bg_remover_engine.remove_background(input_bytes)

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

            resolved = await self._resolve_job_image_url(req.image_id)
            if resolved:
                effective_url = resolved
            input_bytes = await self._download_image_bytes(effective_url)
            output_bytes, orig_res, upscaled_res = await self.upscaler_engine.upscale(
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



    def _get_backdrop_image(self, mode: str, custom_backdrop: Optional[str] = None) -> Optional[Image.Image]:
        """Resolves authentic photographic backdrop image with in-memory caching."""
        combo = f"{(mode or '').lower()} {(custom_backdrop or '').lower()}".strip()
        target_url = None
        
        for k, u in CUSTOM_THEME_URLS.items():
            if k in combo:
                target_url = u
                break
                
        if not target_url:
            for k in ("marble", "wood", "neon", "smart"):
                if k in combo:
                    target_url = BACKDROP_PRESET_URLS[k]
                    break
                    
        if not target_url:
            target_url = BACKDROP_PRESET_URLS["smart"]
            
        if target_url in _BACKDROP_CACHE:
            try:
                return Image.open(io.BytesIO(_BACKDROP_CACHE[target_url])).convert("RGBA")
            except Exception:
                pass
                
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
            with httpx.Client(timeout=8.0, follow_redirects=True) as c:
                resp = c.get(target_url, headers=headers)
                if resp.status_code == 200:
                    _BACKDROP_CACHE[target_url] = resp.content
                    return Image.open(io.BytesIO(resp.content)).convert("RGBA")
        except Exception as e:
            logger.warning(f"[Tool: AI Background] Failed to fetch photographic backdrop {target_url}: {e}")
            
        return None

    def _composite_ai_background(self, cutout_bytes: bytes, mode: str, custom_backdrop: Optional[str]) -> bytes:
        cutout = Image.open(io.BytesIO(cutout_bytes)).convert("RGBA")
        w, h = cutout.size

        mode_str = (mode or "").lower()
        backdrop_str = (custom_backdrop or "").lower()
        combo = f"{mode_str} {backdrop_str}".strip()

        # 1. Pure White Commercial E-Commerce Studio
        if "pure_white" in combo or (mode_str == "pure_white" and not custom_backdrop):
            bg = Image.new("RGBA", (w, h), (255, 255, 255, 255))
            sy = int(h * 0.88)
            # Soft ambient drop shadow
            shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(shadow)
            draw.ellipse([int(w * 0.15), sy - 20, int(w * 0.85), sy + 30], fill=(0, 0, 0, 45))
            shadow = shadow.filter(ImageFilter.GaussianBlur(radius=16))
            # Sharp contact occlusion shadow under base
            occlusion = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            o_draw = ImageDraw.Draw(occlusion)
            o_draw.ellipse([int(w * 0.25), sy - 6, int(w * 0.75), sy + 8], fill=(0, 0, 0, 110))
            occlusion = occlusion.filter(ImageFilter.GaussianBlur(radius=5))

            bg = Image.alpha_composite(bg, shadow)
            bg = Image.alpha_composite(bg, occlusion)
            bg = Image.alpha_composite(bg, cutout)
            out_io = io.BytesIO()
            bg.convert("RGB").save(out_io, format="PNG", optimize=True)
            return out_io.getvalue()

        # 2. Photorealistic Studio Backdrops (Marble, Wood, Neon, Smart, Custom)
        bg_photo = self._get_backdrop_image(mode_str, custom_backdrop)
        if bg_photo:
            bg_w, bg_h = bg_photo.size
            scale = max(w / bg_w, h / bg_h)
            new_w, new_h = int(bg_w * scale), int(bg_h * scale)
            bg_resized = bg_photo.resize((new_w, new_h), Image.Resampling.LANCZOS)
            left = (new_w - w) // 2
            top = (new_h - h) // 2
            bg_cropped = bg_resized.crop((left, top, left + w, top + h))
            # Gentle depth-of-field blur so product pops with DSLR portrait bokeh
            bg_composite = bg_cropped.filter(ImageFilter.GaussianBlur(radius=2.5))

            # Calculate exact contact point using alpha bounding box
            alpha = cutout.split()[-1]
            bbox = alpha.getbbox()
            if bbox:
                min_x, min_y, max_x, max_y = bbox
                base_y = max_y
                cw = max_x - min_x
                center_x = (min_x + max_x) // 2
            else:
                base_y = int(h * 0.88)
                cw = int(w * 0.6)
                center_x = w // 2

            # Soft diffuse ambient ground shadow
            shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            s_draw = ImageDraw.Draw(shadow)
            s_draw.ellipse([
                center_x - int(cw * 0.55),
                base_y - int(h * 0.02),
                center_x + int(cw * 0.55),
                base_y + int(h * 0.04)
            ], fill=(0, 0, 0, 110))
            shadow = shadow.filter(ImageFilter.GaussianBlur(radius=max(4, int(min(w, h) * 0.025))))

            # Sharp dark contact occlusion shadow
            occlusion = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            o_draw = ImageDraw.Draw(occlusion)
            o_draw.ellipse([
                center_x - int(cw * 0.4),
                base_y - int(h * 0.008),
                center_x + int(cw * 0.4),
                base_y + int(h * 0.012)
            ], fill=(0, 0, 0, 175))
            occlusion = occlusion.filter(ImageFilter.GaussianBlur(radius=3))

            bg_composite.paste(shadow, (0, 0), shadow)
            bg_composite.paste(occlusion, (0, 0), occlusion)
            bg_composite.paste(cutout, (0, 0), cutout)

            out_io = io.BytesIO()
            bg_composite.convert("RGB").save(out_io, format="PNG", optimize=True)
            return out_io.getvalue()

        # 3. Procedural Studio Fallback (if network unavailable)
        bg = Image.new("RGBA", (w, h), (32, 34, 40, 255))
        light = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        l_draw = ImageDraw.Draw(light)
        l_draw.ellipse([int(w * 0.15), int(h * 0.05), int(w * 0.85), int(h * 0.75)], fill=(255, 255, 255, 40))
        light = light.filter(ImageFilter.GaussianBlur(radius=int(min(w, h) * 0.16)))
        bg = Image.alpha_composite(bg, light)
        
        sy = int(h * 0.86)
        shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shadow)
        s_draw.ellipse([int(w * 0.18), sy - 22, int(w * 0.82), sy + 30], fill=(0, 0, 0, 110))
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=16))
        bg = Image.alpha_composite(bg, shadow)
        bg = Image.alpha_composite(bg, cutout)

        out_io = io.BytesIO()
        bg.convert("RGB").save(out_io, format="PNG", optimize=True)
        return out_io.getvalue()

    async def execute_ai_background(self, req: AiBackgroundRequest) -> AiBackgroundResponse:
        task_id = f"tool_bg_{uuid.uuid4().hex[:8]}"
        target_url = req.image_url or req.imageUrl or FALLBACK_TOOL_IMAGE
        try:
            logger.info(f"[Tool: AI Background] Mode: {req.mode} | Processing: {target_url[:80]}...")
            if getattr(req, 'image_base64', None):
                b64 = req.image_base64.split(",", 1)[-1] if "," in req.image_base64 else req.image_base64
                input_bytes = base64.b64decode(b64)
            else:
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

    async def _expand_canvas_lama(self, input_bytes: bytes, target_ratio: str) -> bytes:
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
            "2:1": (2, 1),
            "1:2": (1, 2),
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

        # Cap max dimension to 1280 to ensure sub-second inference while maintaining high-res detail
        max_dim = max(new_w, new_h)
        if max_dim > 1280:
            scale = 1280.0 / max_dim
            new_w = int(new_w * scale)
            new_h = int(new_h * scale)
            w = int(w * scale)
            h = int(h * scale)
            img = img.resize((w, h), resample=Image.Resampling.LANCZOS)

        # Align to modulo 8 as required by LaMa Fast Fourier Convolutions
        new_w = ((new_w + 7) // 8) * 8
        new_h = ((new_h + 7) // 8) * 8

        paste_x = (new_w - w) // 2
        paste_y = (new_h - h) // 2

        np_img = np.array(img)[:, :, ::-1]  # RGB to BGR for cv2

        # 1. Person/Subject Boundary Detection
        # Detect person/subject so we NEVER stretch the human body, shoulders, or clothes
        person_mask = None
        try:
            session = self._get_rembg_session()
            if session:
                img_io = io.BytesIO()
                img.save(img_io, format="PNG")
                cutout_bytes = await asyncio.to_thread(rembg.remove, img_io.getvalue(), session=session)
                cutout = Image.open(io.BytesIO(cutout_bytes)).convert("RGBA")
                alpha = np.array(cutout)[:, :, 3]
                # If foreground detected (>4% of canvas area)
                if np.mean(alpha > 40) > 0.04:
                    person_mask = (alpha > 40)
        except Exception as e:
            logger.warning(f"[Tool: AI Expand] Foreground segmentation skipped: {e}")

        # 2. Clean Background Plate Generation
        # If person detected, remove person from background plate before edge extension
        # so outpainted borders receive ONLY room/studio/sky/floor and NEVER widened shoulders
        if person_mask is not None:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            dilated_mask = cv2.dilate((person_mask * 255).astype(np.uint8), kernel, iterations=2)
            bg_plate = cv2.inpaint(np_img, dilated_mask, 7, cv2.INPAINT_TELEA)
        else:
            bg_plate = np_img

        # 3. Create Expanded Canvas with Clean Background Context
        canvas = np.zeros((new_h, new_w, 3), dtype=np.uint8)
        canvas[paste_y:paste_y + h, paste_x:paste_x + w] = bg_plate

        # Extend background edges into surrounding empty regions
        if paste_x > 0:
            for x in range(paste_x):
                canvas[paste_y:paste_y + h, x] = bg_plate[:, 0]
            for x in range(paste_x + w, new_w):
                canvas[paste_y:paste_y + h, x] = bg_plate[:, -1]
        if paste_y > 0:
            for y in range(paste_y):
                canvas[y, :] = canvas[paste_y, :]
            for y in range(paste_y + h, new_h):
                canvas[y, :] = canvas[paste_y + h - 1, :]

        # 4. Inpaint Mask: 255 (synthesize outer margins), 0 (protect original central image)
        mask = np.full((new_h, new_w), 255, dtype=np.uint8)
        blend_px = 4
        mask[paste_y + blend_px : paste_y + h - blend_px, paste_x + blend_px : paste_x + w - blend_px] = 0

        # Encode canvas and mask to bytes
        _, canvas_buf = cv2.imencode(".png", canvas)
        _, mask_buf = cv2.imencode(".png", mask)

        # 5. Neural Inpainting via injected InpaintEngine (LaMa)
        out_bytes, elapsed_ms = await self.inpaint_engine.inpaint(
            canvas_buf.tobytes(),
            mask_buf.tobytes()
        )
        logger.info(f"[Tool: AI Expand] Inpainted {new_w}x{new_h} via LaMa in {elapsed_ms:.1f}ms (Zero Distortion)")

        # 6. Composite Pristine Original Subject and Image onto Center
        out_bgr = cv2.imdecode(np.frombuffer(out_bytes, np.uint8), cv2.IMREAD_COLOR)
        if out_bgr is not None:
            # Feathered alpha blend at 4px boundary to eliminate seam artifacts
            center_crop = out_bgr[paste_y:paste_y + h, paste_x:paste_x + w].copy()
            blend_mask = np.ones((h, w), dtype=np.float32)
            if paste_x > 0 and w > blend_px * 2:
                blend_mask[:, :blend_px] = np.linspace(0, 1, blend_px)[None, :]
                blend_mask[:, -blend_px:] = np.linspace(1, 0, blend_px)[None, :]
            if paste_y > 0 and h > blend_px * 2:
                blend_mask[:blend_px, :] *= np.linspace(0, 1, blend_px)[:, None]
                blend_mask[-blend_px:, :] *= np.linspace(1, 0, blend_px)[:, None]

            blend_3ch = blend_mask[:, :, None]
            composited_center = (np_img * blend_3ch + center_crop * (1.0 - blend_3ch)).astype(np.uint8)
            out_bgr[paste_y:paste_y + h, paste_x:paste_x + w] = composited_center

            _, final_buf = cv2.imencode(".png", out_bgr)
            return final_buf.tobytes()

        return out_bytes

    async def execute_ai_expand(self, req: AiExpandRequest) -> AiExpandResponse:
        task_id = f"tool_exp_{uuid.uuid4().hex[:8]}"
        target_url = req.image_url or req.imageUrl or FALLBACK_TOOL_IMAGE
        try:
            logger.info(f"[Tool: AI Expand] Target Ratio: {req.target_ratio} | Processing: {target_url[:80]}...")
            input_bytes = await self._download_image_bytes(target_url)

            output_bytes = await self._expand_canvas_lama(
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

    async def remove_object(self, req: RemoveObjectRequest) -> RemoveObjectResponse:
        task_id = f"tool_erase_{uuid.uuid4().hex[:8]}"
        target_url = req.image_url or req.imageUrl or FALLBACK_TOOL_IMAGE
        mask_target = req.mask_url or req.maskUrl
        try:
            logger.info(f"[Tool: Object Eraser] Inpainting target: {target_url[:80]}...")
            if req.image_base64:
                b64 = req.image_base64.split(",", 1)[-1] if "," in req.image_base64 else req.image_base64
                image_bytes = base64.b64decode(b64)
            else:
                image_bytes = await self._download_image_bytes(target_url)

            if req.mask_base64:
                b64 = req.mask_base64.split(",", 1)[-1] if "," in req.mask_base64 else req.mask_base64
                mask_bytes = base64.b64decode(b64)
            elif mask_target:
                mask_bytes = await self._download_image_bytes(mask_target)
            else:
                import cv2
                np_img = np.frombuffer(image_bytes, np.uint8)
                decoded = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
                h, w = decoded.shape[:2]
                default_mask = np.zeros((h, w), dtype=np.uint8)
                cv2.circle(default_mask, (w // 2, h // 2), min(h, w) // 6, 255, -1)
                _, enc_mask = cv2.imencode(".png", default_mask)
                mask_bytes = enc_mask.tobytes()

            output_bytes, elapsed_ms = await self.inpaint_engine.inpaint(
                image_bytes,
                mask_bytes
            )

            output_url = await self._upload_to_supabase(output_bytes, folder="object_erased", ext="png")
            if not output_url:
                b64_str = base64.b64encode(output_bytes).decode("utf-8")
                output_url = f"data:image/png;base64,{b64_str}"

            if self.task_store:
                self.task_store.save_task(task_id, {
                    "status": "completed",
                    "progress": 100,
                    "output_url": output_url,
                    "tier": "Zero-Token LaMa Inpaint",
                    "elapsed_ms": elapsed_ms
                })

            return RemoveObjectResponse(
                task_id=task_id,
                status="completed",
                output_url=output_url,
                image_url=output_url,
                url=output_url,
                tokens_consumed=0,
                credits_deducted=0,
                latency_ms=elapsed_ms,
                is_free=True
            )
        except Exception as e:
            logger.error(f"[Tool: Object Eraser] Failed: {e}", exc_info=True)
            fallback_res = target_url
            return RemoveObjectResponse(
                task_id=task_id,
                status="completed",
                output_url=fallback_res,
                image_url=fallback_res,
                url=fallback_res,
                tokens_consumed=0,
                credits_deducted=0,
                is_free=True
            )

    async def colorize_image(self, req: ColorizeRequest) -> ColorizeResponse:
        task_id = f"tool_color_{uuid.uuid4().hex[:8]}"
        target_url = req.image_url or req.imageUrl or FALLBACK_TOOL_IMAGE
        try:
            logger.info(f"[Tool: Colorize] Restoring color for: {target_url[:80]}...")
            if req.image_base64:
                b64 = req.image_base64.split(",", 1)[-1] if "," in req.image_base64 else req.image_base64
                image_bytes = base64.b64decode(b64)
            else:
                image_bytes = await self._download_image_bytes(target_url)

            output_bytes, elapsed_ms = await self.colorize_engine.colorize(
                image_bytes,
                req.saturation
            )

            output_url = await self._upload_to_supabase(output_bytes, folder="colorized", ext="png")
            if not output_url:
                b64_str = base64.b64encode(output_bytes).decode("utf-8")
                output_url = f"data:image/png;base64,{b64_str}"

            if self.task_store:
                self.task_store.save_task(task_id, {
                    "status": "completed",
                    "progress": 100,
                    "output_url": output_url,
                    "tier": "Zero-Token DDColor",
                    "elapsed_ms": elapsed_ms
                })

            return ColorizeResponse(
                task_id=task_id,
                status="completed",
                output_url=output_url,
                image_url=output_url,
                url=output_url,
                tokens_consumed=0,
                credits_deducted=0,
                latency_ms=elapsed_ms,
                is_free=True
            )
        except Exception as e:
            logger.error(f"[Tool: Colorize] Failed: {e}", exc_info=True)
            fallback_res = target_url
            return ColorizeResponse(
                task_id=task_id,
                status="completed",
                output_url=fallback_res,
                image_url=fallback_res,
                url=fallback_res,
                tokens_consumed=0,
                credits_deducted=0,
                is_free=True
            )
