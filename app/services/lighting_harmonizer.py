import cv2
import numpy as np
from PIL import Image
from typing import Tuple

class LightingHarmonizer:
    """
    Simulates physical ambient light wrap and color temperature transfer.
    Harmonizes foreground cutouts with new background plates (Canva / Photoroom parity).
    Prevents the artificial 'cutout sticker' look by transferring background ambient tone
    and creating a feathered edge rim light along the subject silhouette.
    """

    @staticmethod
    def harmonize(cutout_img: Image.Image, bg_img: Image.Image, blend_intensity: float = 0.08) -> Image.Image:
        """
        Transfers ambient color temperature from bg_img onto cutout_img and synthesizes an edge rim light.
        Returns a harmonized RGBA PIL Image.
        """
        try:
            cutout_rgba = np.array(cutout_img.convert("RGBA"))
            cw, ch = cutout_img.size

            # Resize background to match cutout for pixel-level lighting sampling
            bg_resized = bg_img.resize((cw, ch), Image.Resampling.LANCZOS).convert("RGB")
            bg_rgb = np.array(bg_resized)

            alpha = cutout_rgba[:, :, 3]
            if np.sum(alpha > 20) < 50:
                return cutout_img

            fg_rgb = cutout_rgba[:, :, :3]

            # 1. Color Temperature Transfer in CIELAB space
            bg_lab = cv2.cvtColor(bg_rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
            fg_lab = cv2.cvtColor(fg_rgb, cv2.COLOR_RGB2LAB).astype(np.float32)

            # Sample average ambient chromatic values (A: Green-Red, B: Blue-Yellow) of background
            mean_bg_a = float(np.mean(bg_lab[:, :, 1]))
            mean_bg_b = float(np.mean(bg_lab[:, :, 2]))

            # Subtle color cast shift towards background ambient lighting
            intensity = np.clip(blend_intensity, 0.02, 0.20)
            fg_lab[:, :, 1] = np.clip(fg_lab[:, :, 1] * (1.0 - intensity) + mean_bg_a * intensity, 0, 255)
            fg_lab[:, :, 2] = np.clip(fg_lab[:, :, 2] * (1.0 - intensity) + mean_bg_b * intensity, 0, 255)

            harmonized_rgb = cv2.cvtColor(fg_lab.astype(np.uint8), cv2.COLOR_LAB2RGB)

            # 2. Feathered Edge Rim Light along outer alpha boundary (Light Wrap)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            alpha_eroded = cv2.erode(alpha, kernel, iterations=1)
            # Rim mask identifies the outer 2-3px edge of the object
            rim_mask = ((alpha > 35) & (alpha_eroded < 220)).astype(np.float32)[:, :, None]

            # Blend background ambient tone into edge rim
            rim_strength = 0.22
            final_rgb = (
                harmonized_rgb.astype(np.float32) * (1.0 - rim_mask * rim_strength) +
                bg_rgb.astype(np.float32) * (rim_mask * rim_strength)
            ).clip(0, 255).astype(np.uint8)

            cutout_rgba[:, :, :3] = final_rgb
            return Image.fromarray(cutout_rgba, mode="RGBA")
        except Exception:
            return cutout_img

