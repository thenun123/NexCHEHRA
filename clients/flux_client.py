"""
clients/flux_client.py — Phase 1: Flux Kontext Max image generation
Takes reference image + prompt → returns styled portrait URL
Supports optional product image via Flux Kontext Max Multi endpoint.
"""

import os
import fal_client

from config import (
    FAL_KEY,
    FLUX_MODEL,
    FLUX_MULTI_MODEL,
    FLUX_GUIDANCE_SCALE,
    FLUX_INFERENCE_STEPS,
    FLUX_SAFETY_TOLERANCE,
    REFERENCE_IMAGE_PATH,
    OUTPUT_DIR,
    PRODUCT_PLACEMENTS,
    MASTER_NEGATIVE,
)
from utils import emit_log, resolve_image_source
from clients.imagekit_client import persist_from_url


class FluxKontextClient:
    def __init__(self, session_id: str):
        self.session_id = session_id
        os.environ["FAL_KEY"] = FAL_KEY

    def generate(self, flux_prompt: str, shot_config: dict, session_id: str = None,
                 product_image_path: str = None, product_placement: str = None,
                 reference_image_path: str = None, gender: str = "unknown",
                 body_type: str = "normal", aspect_ratio: str = "9:16") -> str:
        """
        Generate a styled portrait using Flux Kontext Max.
        If product_image_path is provided, uses the Multi endpoint with both images.
        reference_image_path overrides the default REFERENCE_IMAGE_PATH.
        aspect_ratio controls the output image dimensions ("16:9" or "9:16").
        Returns (local_file_path, image_url).
        """
        sid = session_id or self.session_id

        def _is_valid_source(p):
            """A usable image source is either a real http(s) URL (ImageKit) or a local file that exists (dev)."""
            return bool(p) and (p.startswith(("http://", "https://")) or os.path.exists(p))

        has_product = _is_valid_source(product_image_path)

        # Determine which reference image to use
        ref_path = reference_image_path if _is_valid_source(reference_image_path) else REFERENCE_IMAGE_PATH

        if has_product:
            return self._generate_with_product(flux_prompt, shot_config, sid,
                                                product_image_path, product_placement,
                                                ref_path, gender, body_type, aspect_ratio)
        else:
            return self._generate_plain(flux_prompt, shot_config, sid,
                                        ref_path, gender, body_type, aspect_ratio)

    def _build_face_prefix(self, gender: str, body_type: str) -> str:
        """Build dynamic face preservation prefix based on gender and body type."""
        if gender == 'male':
            person = "same man"
        elif gender == 'female':
            person = "same woman"
        else:
            person = "same person"

        parts = [f"{person} with exact same face, same facial structure, same skin texture"]

        if body_type == 'chubby':
            parts.append("same chubby stocky build, same thick body type")

        parts.append("same hair")
        return ", ".join(parts)

    def _sanitize_flux_prompt(self, flux_prompt: str) -> str:
        """Remove shot type phrases and person-reference prefixes from flux_prompt.
        LLMs occasionally leak 'same woman/man/person' despite instructions —
        strip them here as a guaranteed code-level fix."""
        import re
        # Remove shot type phrases that override face framing
        shot_phrases = [
            r'full[- ]?body shot',
            r'half[- ]?body shot',
            r'headshot',
            r'close[- ]?up shot',
            r'full[- ]?body',
            r'half[- ]?body',
        ]
        cleaned = flux_prompt
        for phrase in shot_phrases:
            cleaned = re.sub(phrase, '', cleaned, flags=re.IGNORECASE)

        # Strip person-reference prefixes that the LLM sometimes adds
        # (face preservation is handled by KEEP directives in full_prompt)
        person_prefixes = [
            r'^same\s+woman[,\s]+',
            r'^same\s+man[,\s]+',
            r'^same\s+person[,\s]+',
            r'^the\s+person\s+from\s+image\s+\d+[,\s]+',
        ]
        for prefix in person_prefixes:
            cleaned = re.sub(prefix, '', cleaned, flags=re.IGNORECASE)

        # Clean up double commas/spaces left behind
        cleaned = re.sub(r',\s*,', ',', cleaned)
        cleaned = re.sub(r'\s{2,}', ' ', cleaned)
        return cleaned.strip(', ')

    def _generate_plain(self, flux_prompt: str, shot_config: dict, sid: str,
                        ref_path: str, gender: str = "unknown",
                        body_type: str = "normal", aspect_ratio: str = "9:16") -> tuple:
        """Standard single-image flow — no product."""
        emit_log(sid, "processing", "📸 Phase 1: Generating portrait with Flux Kontext...")
        emit_log(sid, "info", f"Model: {FLUX_MODEL}")
        emit_log(sid, "info", f"Reference: {ref_path}")

        # Convert local reference image to data URI
        emit_log(sid, "processing", "📤 Preparing reference image...")
        reference_url = resolve_image_source(ref_path)
        emit_log(sid, "success", "✓ Reference image ready")

        # Build prompt — KEEP face first, then scope what can change (clothing + background)
        face_prefix = self._build_face_prefix(gender, body_type)
        clean_flux  = self._sanitize_flux_prompt(flux_prompt)  # strip any leaked person refs

        # Resolve image dimensions from aspect ratio — Kling O3 anchors video to input image size
        dims = shot_config.get("dimensions", {}).get(aspect_ratio) \
               or shot_config.get("dimensions", {}).get("9:16", {"flux_width": 768, "flux_height": 1344})
        img_width  = dims["flux_width"]
        img_height = dims["flux_height"]
        emit_log(sid, "info", f"📍 Aspect ratio: {aspect_ratio} → {img_width}×{img_height}px")

        # For full_body shots, explicitly replace lower body too (Flux may leave
        is_full_body = "full body" in shot_config.get("shot_phrase", "").lower()
        lower_body_directive = (
            "Replace the ENTIRE body clothing from head to toe — "
            "replace BOTH the upper body clothing AND the lower body clothing (pants/skirt/shorts) AND footwear (shoes/boots/sandals). "
            "Do NOT keep the original pants or shoes — change everything as described. "
        ) if is_full_body else ""

        full_prompt = (
            "KEEP the face IDENTICAL to the reference image — do not change the face, "
            "eyes, nose, mouth, skin tone, facial structure, or hair in any way. "
            "KEEP face pixel-perfect as in the reference. "
            f"ONLY change the clothing and background: {clean_flux}. "
            f"{lower_body_directive}"
            "Replace the background/setting as described. "
            "Do NOT alter face, facial features, or hair at all. "
            f"{face_prefix}. "
            "Photorealistic."
        )

        emit_log(sid, "processing", f"🎨 Sending to {FLUX_MODEL}...")
        emit_log(sid, "info", f"Prompt: {full_prompt[:100]}...")
        emit_log(sid, "info", f"Dimensions: {img_width}x{img_height} ({aspect_ratio})")

        try:
            handler = fal_client.submit(
                FLUX_MODEL,
                arguments={
                    "image_url":         reference_url,
                    "prompt":            full_prompt,
                    "negative_prompt":   MASTER_NEGATIVE,
                    "guidance_scale":    FLUX_GUIDANCE_SCALE,
                    "num_inference_steps": FLUX_INFERENCE_STEPS,
                    "num_images":        1,
                    "output_format":     "jpeg",
                    "safety_tolerance":  FLUX_SAFETY_TOLERANCE,
                    "image_size":        {"width": img_width, "height": img_height},
                },
            )

            emit_log(sid, "processing", "⏳ Flux generating portrait... (30-60s)")
            result = handler.get()

            images = result.get("images", [])
            if not images:
                raise ValueError("No images returned from Flux Kontext")

            image_url = images[0].get("url")
            if not image_url:
                raise ValueError("Image URL missing in Flux response")

            # Log actual image dimensions returned by Flux
            img_width = images[0].get("width", "unknown")
            img_height = images[0].get("height", "unknown")
            emit_log(sid, "success", f"✓ Portrait generated — Dimensions: {img_width}x{img_height} (requested: {aspect_ratio})")

            # Persist to ImageKit (falls back to local OUTPUT_DIR if ImageKit isn't configured)
            filename  = f"portrait_{sid}.jpg"
            save_path = persist_from_url(
                image_url, filename, subfolder="outputs",
                category="output", subtype="image", session_id=sid,
            )

            emit_log(sid, "success", f"✓ Portrait saved: {filename}")
            return save_path, image_url

        except Exception as e:
            emit_log(sid, "error", f"❌ Flux error: {str(e)}")
            raise

    def _generate_with_product(self, flux_prompt: str, shot_config: dict, sid: str,
                                product_image_path: str, product_placement: str = None,
                                ref_path: str = None, gender: str = "unknown",
                                body_type: str = "normal", aspect_ratio: str = "9:16") -> tuple:
        """Multi-image flow — reference image + product image."""
        emit_log(sid, "processing", "📸 Phase 1: Generating portrait WITH PRODUCT...")
        emit_log(sid, "info", f"Model: {FLUX_MULTI_MODEL} (multi-image)")
        emit_log(sid, "info", f"Reference: {ref_path or REFERENCE_IMAGE_PATH}")

        # Prepare both images as data URIs
        emit_log(sid, "processing", "📤 Preparing reference image + product image...")
        reference_uri = resolve_image_source(ref_path or REFERENCE_IMAGE_PATH)
        product_uri   = resolve_image_source(product_image_path)
        emit_log(sid, "success", "✓ Both images ready")

        # Build placement-aware prompt
        placement_desc = ""
        if product_placement:
            placement_desc = PRODUCT_PLACEMENTS.get(product_placement, PRODUCT_PLACEMENTS["in_hand"])

        # Resolve image dimensions from aspect ratio — Kling O3 anchors video to input image size
        dims = shot_config.get("dimensions", {}).get(aspect_ratio) \
               or shot_config.get("dimensions", {}).get("9:16", {"flux_width": 768, "flux_height": 1344})
        img_width  = dims["flux_width"]
        img_height = dims["flux_height"]
        emit_log(sid, "info", f"📍 Aspect ratio: {aspect_ratio} → {img_width}×{img_height}px")

        # Build prompt — KEEP face first, then scope what can change (clothing + background + product)
        face_prefix = self._build_face_prefix(gender, body_type)
        clean_flux  = self._sanitize_flux_prompt(flux_prompt)  # strip any leaked person refs
        full_prompt = (
            "KEEP the face from image 1 IDENTICAL — do not change the face, "
            "eyes, nose, mouth, skin tone, facial structure, or hair in any way. "
            "KEEP face pixel-perfect as it appears in image 1. "
            f"ONLY change the clothing and background: {clean_flux}. "
            "Replace the outfit completely with the new clothing described. "
            "Replace the background/setting as described. "
            f"{placement_desc}. "
            "KEEP the exact product appearance from image 2. "
            "The product from image 2 MUST be at its actual real-world physical size relative to the person — "
            "not oversized or miniature, realistic proportional scale as in real life. "
            "If product is a phone it should be phone-sized, if a bottle then bottle-sized. "
            "Do NOT alter face, facial features, or hair at all. "
            f"{face_prefix}. "
            "Photorealistic."
        )

        emit_log(sid, "processing", f"🎨 Sending to {FLUX_MULTI_MODEL}...")
        emit_log(sid, "info", f"Prompt: {full_prompt[:120]}...")
        emit_log(sid, "info", f"Placement: {product_placement or 'in_hand'}")
        emit_log(sid, "info", f"Dimensions: {img_width}x{img_height} ({aspect_ratio})")

        try:
            handler = fal_client.submit(
                FLUX_MULTI_MODEL,
                arguments={
                    "image_urls":        [reference_uri, product_uri],
                    "prompt":            full_prompt,
                    "negative_prompt":   MASTER_NEGATIVE,
                    "guidance_scale":    FLUX_GUIDANCE_SCALE,
                    "num_inference_steps": FLUX_INFERENCE_STEPS,
                    "num_images":        1,
                    "output_format":     "jpeg",
                    "safety_tolerance":  FLUX_SAFETY_TOLERANCE,
                    "image_size":        {"width": img_width, "height": img_height},
                },
            )

            emit_log(sid, "processing", "⏳ Flux generating portrait with product... (30-90s)")
            result = handler.get()

            images = result.get("images", [])
            if not images:
                raise ValueError("No images returned from Flux Kontext Multi")

            image_url = images[0].get("url")
            if not image_url:
                raise ValueError("Image URL missing in Flux Multi response")

            # Log actual image dimensions returned by Flux
            img_width = images[0].get("width", "unknown")
            img_height = images[0].get("height", "unknown")
            emit_log(sid, "success", f"✓ Portrait with product generated — Dimensions: {img_width}x{img_height} (requested: {aspect_ratio})")

            # Persist to ImageKit (falls back to local OUTPUT_DIR if ImageKit isn't configured)
            filename  = f"portrait_{sid}.jpg"
            save_path = persist_from_url(
                image_url, filename, subfolder="outputs",
                category="output", subtype="image", session_id=sid,
            )

            emit_log(sid, "success", f"✓ Portrait saved: {filename}")
            return save_path, image_url

        except Exception as e:
            emit_log(sid, "error", f"❌ Flux Multi error: {str(e)}")
            raise
