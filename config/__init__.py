"""
config — Application configuration package
Re-exports all settings so `from config import X` continues to work.
"""

from config.settings import *
from config.settings import validate

__all__ = [
    # fal.ai
    "FAL_KEY",
    # Mistral
    "MISTRAL_API_KEY",
    "MISTRAL_MODEL",
    # RAG Knowledge Base
    "KNOWLEDGE_BASE_DIR",
    # Flux Kontext
    "FLUX_MODEL",
    "FLUX_GUIDANCE_SCALE",
    "FLUX_INFERENCE_STEPS",
    "FLUX_SAFETY_TOLERANCE",
    "FLUX_MULTI_MODEL",
    # Kling V3
    "KLING_MODEL",
    "KLING_LANGUAGES",
    # Product Placement
    "PRODUCT_PLACEMENTS",
    # Video
    "VIDEO_DURATION",
    "SCRIPT_MIN_WORDS",
    "SCRIPT_MAX_WORDS",
    "WORDS_PER_SECOND",
    "DEFAULT_ASPECT_RATIO",
    # App
    "FLASK_PORT",
    "FLASK_DEBUG",
    "FLASK_SECRET_KEY",
    "REFERENCE_IMAGE_PATH",
    "OUTPUT_DIR",
    # Supabase
    "DATABASE_URL",
    # ImageKit
    "IMAGEKIT_PUBLIC_KEY",
    "IMAGEKIT_PRIVATE_KEY",
    "IMAGEKIT_URL_ENDPOINT",
    "IMAGEKIT_ROOT_FOLDER",
    "IMAGEKIT_ENABLED",
    # Pricing
    "KLING_PRICING",
    # Shot Types
    "SHOT_TYPE_CONFIGS",
    # Negative Prompt
    "MASTER_NEGATIVE",
    # Validation
    "validate",
]
