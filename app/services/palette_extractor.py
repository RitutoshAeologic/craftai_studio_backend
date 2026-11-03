import cv2
import numpy as np
from PIL import Image
from typing import List, Tuple

class PaletteExtractor:
    """
    Extracts dominant brand and visual palette colors from images (Canva Magic Design parity).
    Uses k-means color quantization in RGB space to identify primary, accent, and contrast colors.
    """

    @staticmethod
    def extract_dominant_colors(pil_img: Image.Image, k: int = 3) -> List[Tuple[int, int, int]]:
        """
        Extracts k dominant RGB colors from a PIL Image.
        Returns a list of (R, G, B) tuples sorted by visual prominence.
        """
        try:
            # Resize image to thumbnail for instant sub-millisecond clustering
            img = pil_img.resize((120, 120), Image.Resampling.BOX).convert("RGB")
            np_img = np.array(img).reshape(-1, 3).astype(np.float32)

            # Filter out pure black/white extremes to capture meaningful brand colors
            luminance = 0.299 * np_img[:, 0] + 0.587 * np_img[:, 1] + 0.114 * np_img[:, 2]
            valid_mask = (luminance > 25) & (luminance < 235)
            filtered_pixels = np_img[valid_mask]

            if len(filtered_pixels) < 100:
                filtered_pixels = np_img

            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
            k_eff = min(k, len(filtered_pixels))
            _, labels, centers = cv2.kmeans(
                filtered_pixels,
                k_eff,
                None,
                criteria,
                10,
                cv2.KMEANS_RANDOM_CENTERS
            )

            # Count cluster sizes to sort by prominence
            counts = np.bincount(labels.flatten())
            sorted_indices = np.argsort(counts)[::-1]

            dominant = []
            for idx in sorted_indices:
                center = centers[idx]
                dominant.append((int(center[0]), int(center[1]), int(center[2])))

            return dominant if dominant else [(99, 102, 241), (236, 72, 153), (34, 197, 94)]
        except Exception:
            return [(99, 102, 241), (236, 72, 153), (34, 197, 94)]

