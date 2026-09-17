from typing import Dict, Any, Optional, Tuple, List

OPTION_A_PREFIX = "Edit image1 as follows: "

class PromptCompiler:
    """
    Enterprise Visual Director Compiler.
    Translates canonical StructuredPromptMetadata into the optimal dialect
    for the specific target diffusion engine (Flux, SDXL, DALL-E, etc.).
    """

    @staticmethod
    def compile_for_flux(metadata: Optional[Dict[str, Any]], fallback_prompt: str = "") -> str:
        """
        Compiles a photographic, narrative descriptive sentence for Flux.1.
        Flux thrives on natural language, lens optics, lighting, and environmental atmosphere.
        """
        if not metadata:
            return fallback_prompt

        has_option_a = fallback_prompt.strip().startswith(OPTION_A_PREFIX)
        parts: List[str] = []

        subject = metadata.get("subject")
        art_style = metadata.get("art_style")
        environment = metadata.get("environment")
        lighting = metadata.get("lighting")
        camera = metadata.get("camera_optics")

        # Construct photographic visual prose
        if art_style:
            parts.append(art_style.rstrip("."))
        if subject:
            parts.append(f"featuring {subject.rstrip('.')}")
        if environment:
            parts.append(f"set in {environment.rstrip('.')}")
        if lighting:
            parts.append(f"illuminated with {lighting.rstrip('.')}")
        if camera:
            parts.append(f"captured on {camera.rstrip('.')}")

        if not parts:
            return fallback_prompt

        compiled = ", ".join(parts) + "."
        # Capitalize first character
        compiled = compiled[0].upper() + compiled[1:]

        if has_option_a and not compiled.startswith(OPTION_A_PREFIX):
            compiled = f"{OPTION_A_PREFIX}{compiled}"

        return compiled

    @staticmethod
    def compile_for_sdxl(
        metadata: Optional[Dict[str, Any]], 
        fallback_prompt: str = "", 
        extra_negatives: Optional[List[str]] = None
    ) -> Tuple[str, str]:
        """
        Compiles positive and negative conditioning vectors for SDXL.
        SDXL thrives on comma-separated descriptors and heavy negative prompt filtering.
        """
        has_option_a = fallback_prompt.strip().startswith(OPTION_A_PREFIX)
        default_negatives = [
            "blurry", "low quality", "distorted", "deformed", 
            "extra limbs", "bad anatomy", "watermark", "text", "signature"
        ]

        if not metadata:
            neg = ", ".join(extra_negatives or default_negatives)
            return fallback_prompt, neg

        pos_parts: List[str] = []
        for key in ["subject", "environment", "lighting", "camera_optics", "art_style"]:
            val = metadata.get(key)
            if val:
                pos_parts.append(val.rstrip("."))

        pos = ", ".join(pos_parts) if pos_parts else fallback_prompt

        # Build negative prompt
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

    @staticmethod
    def compile_for_target_model(
        model: str,
        metadata: Optional[Dict[str, Any]],
        fallback_prompt: str = "",
        existing_negative_prompt: str = ""
    ) -> Dict[str, str]:
        """
        Inspects the target model and produces the tailored positive and negative prompts.
        """
        target = (model or "flux").lower()

        if "sdxl" in target or "stable" in target:
            pos, neg = PromptCompiler.compile_for_sdxl(metadata, fallback_prompt)
            return {
                "prompt": pos,
                "negative_prompt": neg or existing_negative_prompt
            }
        else:
            # Flux, Gemini, ChatGPT/DALL-E defaults to rich narrative flow
            compiled = PromptCompiler.compile_for_flux(metadata, fallback_prompt)
            # Combine any avoid tags into negative_prompt for engines that support it
            avoid_tokens = metadata.get("avoid", []) if metadata else []
            neg = ", ".join(avoid_tokens) if avoid_tokens else existing_negative_prompt
            return {
                "prompt": compiled,
                "negative_prompt": neg
            }

    @staticmethod
    def merge_structured_deltas(
        current: Optional[Dict[str, Any]], 
        delta: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Merges delta updates into existing structured metadata while respecting preserved_elements.
        """
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
                # Keep preserved field unchanged unless explicitly overridden
                continue
            elif value is not None and str(value).strip():
                merged[key] = value

        return merged
