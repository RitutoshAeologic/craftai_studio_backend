import re
from typing import Dict, Any, Optional, Tuple, List

OPTION_A_PREFIX = "Edit image1 as follows: "

# 2022-era obsolete buzzwords that degrade modern latent models (Flux.1, SD3, Midjourney v6)
BANNED_TAG_SOUP = [
    r"\b8k\b", r"\b4k resolution\b", r"\bmasterpiece\b", r"\bhyperrealistic\b",
    r"\bphotorealistic\b", r"\btrending on artstation\b", r"\bunreal engine 5\b",
    r"\boctane render\b", r"\baward winning\b", r"\bultra detailed\b",
    r"\bhigh quality\b", r"\bbest quality\b", r"\bcgstation\b", r"\bvray\b"
]

class PromptCompiler:
    """
    Enterprise Visual Director Compiler.
    Translates user intents and StructuredPromptMetadata into high-fidelity
    visual directives tailored for modern diffusion backends (Flux.1, SDXL, etc.).
    """

    @classmethod
    def strip_tag_soup(cls, text: str) -> str:
        """Strips toxic 2022 tag soup buzzwords that degrade Flux.1 latents."""
        cleaned = text
        for pattern in BANNED_TAG_SOUP:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        # Clean up repeated commas, double spaces
        cleaned = re.sub(r",\s*,+", ",", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.")
        return cleaned

    @classmethod
    def compile_for_flux(cls, metadata: Optional[Dict[str, Any]], fallback_prompt: str = "") -> str:
        """
        Compiles photographic, narrative descriptive prose for Flux.1.
        Flux thrives on natural camera optics, tactile shaders, and physical lighting.
        """
        clean_fallback = cls.strip_tag_soup(fallback_prompt)
        if not metadata:
            return clean_fallback

        has_option_a = clean_fallback.strip().startswith(OPTION_A_PREFIX)
        parts: List[str] = []

        subject = metadata.get("subject")
        art_style = metadata.get("art_style")
        environment = metadata.get("environment")
        lighting = metadata.get("lighting")
        camera = metadata.get("camera_optics")

        if art_style:
            parts.append(cls.strip_tag_soup(art_style.rstrip(".")))
        if subject:
            parts.append(f"featuring {cls.strip_tag_soup(subject.rstrip('.'))}")
        if environment:
            parts.append(f"set in {cls.strip_tag_soup(environment.rstrip('.'))}")
        if lighting:
            parts.append(f"illuminated with {cls.strip_tag_soup(lighting.rstrip('.'))}")
        if camera:
            parts.append(f"captured on {cls.strip_tag_soup(camera.rstrip('.'))}")

        if not parts:
            return clean_fallback

        compiled = ", ".join(parts) + "."
        compiled = compiled[0].upper() + compiled[1:]

        if has_option_a and not compiled.startswith(OPTION_A_PREFIX):
            compiled = f"{OPTION_A_PREFIX}{compiled}"

        return compiled

    @classmethod
    def compile_for_marketing_poster(
        cls, 
        topic: str, 
        category: str = "Commercial", 
        aspect_ratio: str = "4:5",
        headline: Optional[str] = None,
        language: str = "Auto"
    ) -> str:
        """
        Compiles commercial advertising poster prompts with clear layout,
        bold negative space, and typographic focus tailored for Flux text synthesis.
        """
        clean_topic = cls.strip_tag_soup(topic or "Special Promotion")
        clean_category = str(category or "Commercial").replace("_", " ").title()
        effective_headline = headline or clean_topic.title()

        lang_clause = ""
        if language and language.strip().lower() not in ["auto", "auto (match my input)", ""]:
            lang_clause = f" Typography and headline copy written in {language}."

        prompt = (
            f"Commercial advertising poster for '{clean_topic}', {clean_category} design. "
            f"Clean minimalist Swiss graphic design layout, bold headline typography reading '{effective_headline}'.{lang_clause} "
            f"High contrast editorial color grading, crisp studio rim lighting, generous negative copy space, "
            f"ultra-sharp branding composition formatted for {aspect_ratio} display."
        )
        return prompt

    @classmethod
    def compile_for_marketing_poster_backdrop(
        cls,
        topic: str,
        category: str = "Commercial",
        aspect_ratio: str = "4:5",
        headline: Optional[str] = None,
        language: str = "Auto"
    ) -> str:
        """
        Compiles commercial advertising poster graphic layout backdrop with clean empty hero center space
        and top headline framing, tailored for compositing user's product without clutter.
        """
        clean_topic = cls.strip_tag_soup(topic or "Special Promotion")
        clean_category = str(category or "Commercial").replace("_", " ").title()
        effective_headline = headline or clean_topic.title()

        lang_clause = ""
        if language and language.strip().lower() not in ["auto", "auto (match my input)", ""]:
            lang_clause = f" Typography and headline copy written in {language}."

        prompt = (
            f"Commercial advertising poster graphic layout backdrop for '{clean_topic}', {clean_category} design. "
            f"Clean minimalist Swiss graphic design framing, bold headline typography reading '{effective_headline}' placed prominently at top.{lang_clause} "
            f"Spacious clean negative space and empty central hero zone reserved for product display, no products in center, no foreground objects, "
            f"high contrast editorial color grading, crisp studio rim lighting, formatted for {aspect_ratio} display."
        )
        return prompt

    @classmethod
    def compile_for_ai_background(
        cls, 
        mode: str, 
        subject_desc: str = "product", 
        custom_backdrop: Optional[str] = None
    ) -> str:
        """
        Compiles realistic scene backdrop prompts that match product perspective and lighting.
        Generates clean empty backdrop scenes with copy space so the user's isolated
        foreground subject is seamlessly composited without hallucinating duplicate objects.
        """
        clean_mode = str(mode or "smart").strip().lower().replace("-", "_").replace(" ", "_")
        if clean_mode in ("pure_white", "purewhite", "white", "studio_white"):
            return "Seamless pure white infinity cyclo studio backdrop, subtle soft contact floor shadow, clean commercial e-commerce lighting."
        elif clean_mode == "smart":
            return (
                "Empty high-end architectural minimalist podium surface and backdrop, clean empty studio stage, "
                "smooth beige travertine stone texture, gentle diffused morning sunlight casting soft geometric shadows, "
                "shallow depth of field, f/2.8 lens blur, spacious center for product placement, no foreground objects, no products, premium catalog aesthetic."
            )
        else:
            backdrop = custom_backdrop or "modern minimalist aesthetic studio"
            return (
                f"Empty photographic commercial backdrop scene: {backdrop}, "
                f"clean empty center surface and platform ready for product display, no foreground objects, no products, professional softbox illumination, cinematic bokeh."
            )

    @classmethod
    def compile_for_product_detail_backdrop(cls, product_name: str = "Product", style: str = "Modern Minimalist") -> str:
        """
        Compiles an empty luxury product showroom stage / cyclo pedestal backdrop
        ready for compositing the user's isolated product without hallucinating duplicate objects.
        """
        clean_name = cls.strip_tag_soup(product_name or "Product")
        return (
            f"Empty luxury commercial product showroom stage for {clean_name}, {style} aesthetic. "
            "Clean empty studio cyclo pedestal, authentic tactile stone and podium textures, soft directional key light with gentle fill, "
            "empty platform ready for product placement, no foreground objects, no duplicate products, 8k commercial presentation."
        )

    @classmethod
    def compile_for_product_detail(cls, product_name: str = "Product", style: str = "Modern Minimalist", language: str = "Auto") -> str:
        """
        Compiles e-commerce product feature listing set with macro texture and exploded angle views.
        """
        clean_name = cls.strip_tag_soup(product_name or "Product")
        lang_clause = ""
        if language and language.strip().lower() not in ["auto", "auto (match my input)", ""]:
            lang_clause = f" Feature annotations and callout text written in {language}."

        return (
            f"Professional e-commerce listing hero shot of {clean_name}, {style} aesthetic.{lang_clause} "
            "Clean studio cyclo pedestal, authentic tactile material texture, soft directional key light with gentle fill, "
            "tack-sharp focus on craftsmanship details, high commercial conversion presentation."
        )

    @classmethod
    def compile_for_expand(cls, target_ratio: str, scene_context: str = "") -> str:
        """
        Compiles seamless outpainting extension directives.
        """
        context = scene_context or "the existing natural environment"
        return (
            f"Seamless generative canvas extension to {target_ratio} aspect ratio. "
            f"Naturally continues {context}, perfectly matching atmospheric horizon, lighting direction, and color temperature."
        )

    @classmethod
    def compile_for_sdxl(
        cls,
        metadata: Optional[Dict[str, Any]], 
        fallback_prompt: str = "", 
        extra_negatives: Optional[List[str]] = None
    ) -> Tuple[str, str]:
        """SDXL positive and negative conditioning vectors."""
        has_option_a = fallback_prompt.strip().startswith(OPTION_A_PREFIX)
        default_negatives = [
            "blurry", "low quality", "distorted", "deformed", 
            "extra limbs", "bad anatomy", "watermark", "text", "signature"
        ]

        if not metadata:
            neg = ", ".join(extra_negatives or default_negatives)
            return cls.strip_tag_soup(fallback_prompt), neg

        pos_parts: List[str] = []
        for key in ["subject", "environment", "lighting", "camera_optics", "art_style"]:
            val = metadata.get(key)
            if val:
                pos_parts.append(cls.strip_tag_soup(val.rstrip(".")))

        pos = ", ".join(pos_parts) if pos_parts else cls.strip_tag_soup(fallback_prompt)

        avoid_list = list(metadata.get("avoid", []))
        if extra_negatives:
            avoid_list.extend(extra_negatives)
        for neg in default_negatives:
            if neg not in avoid_list:
                avoid_list.append(neg)

        neg_prompt = ", ".join(avoid_list)

        if has_option_a and not pos.startswith(OPTION_A_PREFIX):
            pos = f"{OPTION_A_PREFIX}{pos}"

        return pos, neg_prompt

    @classmethod
    def compile_for_target_model(
        cls,
        model: str,
        metadata: Optional[Dict[str, Any]],
        fallback_prompt: str = "",
        existing_negative_prompt: str = ""
    ) -> Dict[str, str]:
        target = (model or "flux").lower()

        if "sdxl" in target or "stable" in target:
            pos, neg = cls.compile_for_sdxl(metadata, fallback_prompt)
            return {
                "prompt": pos,
                "negative_prompt": neg or existing_negative_prompt
            }
        else:
            compiled = cls.compile_for_flux(metadata, fallback_prompt)
            avoid_tokens = metadata.get("avoid", []) if metadata else []
            neg = ", ".join(avoid_tokens) if avoid_tokens else existing_negative_prompt
            return {
                "prompt": compiled,
                "negative_prompt": neg
            }

    @classmethod
    def merge_structured_deltas(
        cls, 
        current: Optional[Dict[str, Any]], 
        delta: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not current:
            return delta or {}
        if not delta:
            return current

        merged = dict(current)
        preserved = set(current.get("preserved_elements", []))

        for key, value in delta.items():
            if key == "preserved_elements":
                new_preserved = set(value) if isinstance(value, list) else set()
                merged["preserved_elements"] = list(preserved.union(new_preserved))
            elif key == "avoid":
                existing_avoid = set(current.get("avoid", []))
                new_avoid = set(value) if isinstance(value, list) else set()
                merged["avoid"] = list(existing_avoid.union(new_avoid))
            elif key in preserved:
                continue
            elif value is not None and str(value).strip():
                merged[key] = value

        return merged
