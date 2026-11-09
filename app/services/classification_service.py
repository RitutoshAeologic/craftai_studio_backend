import re
from typing import List, Dict, Optional
from app.core.logging import logger

class CategoryClassifier:
    """
    Intelligent Multi-Stage Visual Category Classifier.
    Prioritizes deterministic style preset mapping -> regex token scoring -> fallback.
    """

    _STYLE_MAP: Dict[str, str] = {
        "realistic photo": "Photorealism",
        "photoreal": "Photorealism",
        "cinematic art": "Photorealism",
        "hollywood": "Photorealism",
        "3d cartoon": "3D Render",
        "pixar 3d": "3D Render",
        "3d render": "3D Render",
        "anime / manga": "Anime",
        "anime cel": "Anime",
        "anime": "Anime",
        "manga": "Anime",
        "cyberpunk neon": "Cyberpunk",
        "sci-fi neon": "Cyberpunk",
        "cyberpunk": "Cyberpunk",
        "oil painting": "Character",
        "renaissance": "Character",
        "portrait": "Character",
        "character": "Character",
        "architecture": "Architecture",
        "product": "Product",
    }

    _KEYWORDS: Dict[str, List[str]] = {
        "Photorealism": [
            "photo", "photograph", "85mm", "portrait", "realistic", "dslr",
            "raw photo", "kodak", "hyperrealistic", "cinematic still", "film grain",
            "dramatic studio lighting", "ultra-detailed textures"
        ],
        "Anime": [
            "anime", "manga", "ghibli", "shinkai", "makoto shinkai", "cel shaded",
            "waifu", "kawaii", "chibi", "otaku", "japanese animation", "anime aesthetic"
        ],
        "Cyberpunk": [
            "cyberpunk", "neon", "futuristic", "cyborg", "synthwave", "sci-fi",
            "hologram", "mecha", "blade runner", "matrix", "volumetric fog", "neon lights"
        ],
        "3D Render": [
            "3d", "render", "octane", "blender", "unreal engine", "cgi",
            "isometric", "pixar", "claymation", "soft clay render", "ambient occlusion"
        ],
        "Character": [
            "character", "warrior", "knight", "noblewoman", "hero", "villain",
            "person", "avatar", "ethereal noblewoman", "samurai", "ronin", "facial features"
        ],
        "Architecture": [
            "architecture", "building", "house", "interior", "facade", "villa",
            "skyscraper", "room", "castle", "waterfalls", "modern villa", "structure"
        ],
        "Product": [
            "product", "mockup", "bottle", "packaging", "watch", "sneakers",
            "commercial", "perfume", "cosmetics", "gadget", "merchandise", "minimalist"
        ],
    }

    @classmethod
    def classify(cls, prompt: str, explicit_style: Optional[str] = None, explicit_category: Optional[str] = None) -> str:
        """
        Classifies an image generation prompt into its canonical category name.
        """
        # 0. Explicit category passed by client
        if explicit_category and explicit_category.strip():
            clean_cat = explicit_category.strip().lower()
            if clean_cat in cls._STYLE_MAP:
                return cls._STYLE_MAP[clean_cat]
            # Title-case canonical match
            for canonical in cls._KEYWORDS.keys():
                if canonical.lower() == clean_cat:
                    return canonical
            return explicit_category.strip().title()

        # 1. Deterministic style preset mapping
        if explicit_style and explicit_style.strip():
            clean_style = explicit_style.strip().lower()
            if clean_style in cls._STYLE_MAP:
                return cls._STYLE_MAP[clean_style]

        # 2. Fast regex keyword token scoring (0.1ms)
        p_lower = prompt.lower()
        scores: Dict[str, int] = {}
        for cat, keywords in cls._KEYWORDS.items():
            score = 0
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', p_lower):
                    score += 1
            if score > 0:
                scores[cat] = score

        if scores:
            best_cat = max(scores, key=lambda k: scores[k])
            logger.debug(f"[CategoryClassifier] Prompt classified as '{best_cat}' (scores: {scores})")
            return best_cat

        return "General"
