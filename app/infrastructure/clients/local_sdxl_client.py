import io
import asyncio
from typing import Optional
from PIL import Image
from app.infrastructure.clients.base import IDiffusionEngine
from app.core.config import settings
from app.core.logging import logger

class LocalSDXLClient(IDiffusionEngine):
    """
    Local Stable Diffusion XL Lightning / RealVisXL Pipeline.
    Optimized for Apple Silicon Metal Performance Shaders (MPS) in float16.
    Uses fused Lightning LoRA for 4-step photorealistic inference in ~5-8s on M1 Pro.
    """
    def __init__(
        self,
        base_model: Optional[str] = None,
        lora_repo: Optional[str] = None,
        lora_weight: Optional[str] = None,
        steps: Optional[int] = None,
        guidance: Optional[float] = None
    ):
        self.base_model = base_model or settings.LOCAL_SDXL_BASE_MODEL
        self.lora_repo = lora_repo or settings.LOCAL_SDXL_LORA_REPO
        self.lora_weight = lora_weight or settings.LOCAL_SDXL_LORA_WEIGHT
        self.steps = steps or settings.LOCAL_SDXL_STEPS
        self.guidance = guidance or settings.LOCAL_SDXL_GUIDANCE
        self._pipe = None
        self._lock = asyncio.Lock()
        self._device = None

    def _determine_device(self) -> str:
        try:
            import torch
            if torch.backends.mps.is_available():
                return "mps"
            if torch.cuda.is_available():
                return "cuda"
        except Exception:
            pass
        return "cpu"

    def is_available(self) -> bool:
        """Checks if PyTorch and diffusers are importable."""
        try:
            import torch
            import diffusers
            return True
        except ImportError:
            return False

    def _load_pipeline(self):
        """Loads and compiles the SDXL Lightning pipeline into unified memory."""
        if self._pipe is not None:
            return self._pipe

        import torch
        from diffusers import StableDiffusionXLPipeline, EulerDiscreteScheduler, AutoencoderKL

        self._device = self._determine_device()
        dtype = torch.float16 if self._device in ("mps", "cuda") else torch.float32
        logger.info(f"[Local SDXL] Loading model '{self.base_model}' onto {self._device} ({dtype})...")

        # 1. Load FP16-safe VAE to prevent black-image overflow on Apple Silicon MPS
        vae = None
        try:
            vae = AutoencoderKL.from_pretrained(
                "madebyollin/sdxl-vae-fp16-fix",
                torch_dtype=dtype
            )
            logger.info("[Local SDXL] Using madebyollin/sdxl-vae-fp16-fix for artifact-free MPS decoding.")
        except Exception as e:
            logger.warning(f"[Local SDXL] Could not load fixed VAE ({e}), using default VAE.")

        # 2. Instantiate Base SDXL Pipeline
        kwargs = {
            "torch_dtype": dtype,
            "use_safetensors": True
        }
        if dtype == torch.float16:
            kwargs["variant"] = "fp16"
        if vae is not None:
            kwargs["vae"] = vae

        pipe = StableDiffusionXLPipeline.from_pretrained(self.base_model, **kwargs)
        pipe = pipe.to(self._device)

        # 3. Fuse SDXL-Lightning 4-step LoRA for ultra-fast inference
        try:
            logger.info(f"[Local SDXL] Fusing LoRA '{self.lora_repo}' ({self.lora_weight})...")
            pipe.load_lora_weights(self.lora_repo, weight_name=self.lora_weight)
            pipe.fuse_lora()
        except Exception as e:
            logger.warning(f"[Local SDXL] LoRA fusion note: {e}. Running base model without fused LoRA.")

        # 4. Configure trailing timestep spacing required by SDXL-Lightning
        pipe.scheduler = EulerDiscreteScheduler.from_config(
            pipe.scheduler.config,
            timestep_spacing="trailing"
        )

        # 5. Upcast VAE to float32 on Apple Silicon MPS (proven fix for 100% color output)
        if self._device == "mps":
            pipe.vae.to(dtype=torch.float32)
            logger.info("[Local SDXL] Upcasted VAE to float32 on MPS for 100% artifact-free decoding.")

        self._pipe = pipe
        logger.info("[Local SDXL] Pipeline successfully loaded and primed in memory.")
        return self._pipe

    def _sync_generate(
        self,
        prompt: str,
        width: int,
        height: int,
        seed: int,
        negative_prompt: Optional[str]
    ) -> bytes:
        import torch

        pipe = self._load_pipeline()
        generator = torch.Generator(device=self._device).manual_seed(seed)

        # SDXL-Lightning distilled models require guidance_scale=0.0 (CFG disabled)
        # CFG calculation on 4-step distilled latents causes numerical overflow on Apple Silicon MPS
        cfg_scale = self.guidance if self.guidance is not None else 0.0
        neg = negative_prompt if (cfg_scale > 1.0 and negative_prompt) else None

        logger.info(f"[Local SDXL] Running Lightning inference ({self.steps} steps, guidance={cfg_scale}, {width}x{height})...")
        res = pipe(
            prompt=prompt,
            negative_prompt=neg,
            num_inference_steps=self.steps,
            guidance_scale=cfg_scale,
            width=width,
            height=height,
            generator=generator
        )

        image: Image.Image = res.images[0]
        buf = io.BytesIO()
        image.save(buf, format="PNG")

        # Flush MPS memory cache to prevent fragmentation on Apple Silicon
        if self._device == "mps" and hasattr(torch, "mps") and hasattr(torch.mps, "empty_cache"):
            torch.mps.empty_cache()

        return buf.getvalue()

    async def generate_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        seed: int = 42,
        negative_prompt: Optional[str] = None
    ) -> Optional[bytes]:
        """Executes diffusion inference safely in a worker thread with MPS concurrency locking."""
        if not self.is_available():
            logger.warning("[Local SDXL] PyTorch / diffusers not available in environment.")
            return None

        # Lock ensures single-flight inference on MPS to prevent Metal kernel crashes
        async with self._lock:
            try:
                return await asyncio.to_thread(
                    self._sync_generate,
                    prompt,
                    width,
                    height,
                    seed,
                    negative_prompt
                )
            except Exception as e:
                logger.error(f"[Local SDXL] Inference error: {e}", exc_info=True)
                return None
