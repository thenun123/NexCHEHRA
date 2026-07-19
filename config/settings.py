"""
config/settings.py — Loads all settings from .env
No hardcoded values anywhere else in the project.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- fal.ai ---
FAL_KEY                 = os.getenv("FAL_KEY")

# --- Mistral LLM (main prompt generation & RAG chatbot) ---
MISTRAL_API_KEY         = os.getenv("MISTRAL_API_KEY")
MISTRAL_MODEL           = os.getenv("MISTRAL_MODEL", "mistral-large-latest")

# --- Knowledge Base (RAG) ---
KNOWLEDGE_BASE_DIR      = os.getenv("KNOWLEDGE_BASE_DIR", "knowledge_base")

# --- Flux Kontext ---
FLUX_MODEL              = os.getenv("FLUX_MODEL", "fal-ai/flux-pro/kontext/max")
FLUX_GUIDANCE_SCALE     = float(os.getenv("FLUX_GUIDANCE_SCALE", "2.0"))
FLUX_INFERENCE_STEPS    = int(os.getenv("FLUX_INFERENCE_STEPS", "28"))
FLUX_SAFETY_TOLERANCE   = os.getenv("FLUX_SAFETY_TOLERANCE", "2")

# --- Flux Kontext Multi (product placement) ---
FLUX_MULTI_MODEL        = os.getenv("FLUX_MULTI_MODEL", "fal-ai/flux-pro/kontext/max/multi")

# --- Kling V3 (legacy — kept for reference) ---
KLING_MODEL             = os.getenv("KLING_MODEL", "fal-ai/kling-video/v3/pro/image-to-video")

# --- Kling O3 Pro (active video model) ---
KLING_O3_MODEL          = os.getenv("KLING_O3_MODEL", "fal-ai/kling-video/o3/pro/image-to-video")
# O3 Pro Input schema: image_url, prompt, duration (str enum), generate_audio, multi_prompt, shot_type
# NO negative_prompt / cfg_scale / aspect_ratio / voice_ids — those are V1/V2/V3 only

# --- Kling V3 Audio Support ---
# V3 native audio generation:
# - Supports English and Chinese natively
# - Other languages auto-translate to English
# - Use lowercase for natural English speech (except acronyms/proper nouns)
# - Include dialogue in quotes in the prompt: 'person says "Hello everyone"'
# - Optional: Use voice_ids for custom voice cloning (not implemented yet)

KLING_LANGUAGES = {
    "en_us": "English (US)",
    "en_uk": "English (UK)",
    "zh":    "Chinese",
    "ja":    "Japanese",
    "ko":    "Korean",
    "es":    "Spanish",
}

# --- Kling O3 Pricing (per second) ---
KLING_O3_PRICING = {
    "audio_off":  0.112,   # silent video
    "audio_on":   0.168,   # native audio enabled (Pro with audio)
}



# --- Product Placement Options ---
PRODUCT_PLACEMENTS = {
    "in_hand":    "holding the product in one hand at its actual real-world size, product is normal-sized relative to the person's hand, natural casual grip, product should be phone-sized if it's a phone or bottle-sized if it's a bottle",
    "beside":     "with the product placed right beside them at its actual real-world size, product clearly visible but at normal proportions, not oversized or undersized",
    "on_table":   "with the product displayed on a table in front of them at its actual real-world size, product sits naturally on the table at realistic scale, not giant or tiny",
    "background": "with the product visible in the background at realistic real-world proportions, product appears at natural size as it would in a real room",
    "wearing":    "MUST be physically wearing the product on their body — if headphones then ON the head over ears, if glasses then ON the face, if watch then ON the wrist, if necklace then AROUND the neck, if hat then ON the head — product must be actively worn not held in hands, product fits naturally at real-world size, face must remain fully visible even while wearing the product",
}

# --- Video (Kling O3 Pro — 15 seconds) ---
VIDEO_DURATION          = 15   # Kling O3 Pro max 15s
SCRIPT_MIN_WORDS        = 38   # 38-40 words + punctuation fills 15s naturally
SCRIPT_MAX_WORDS        = 40   # ceiling — AI voice slows down at commas/em-dashes
WORDS_PER_SECOND        = float(os.getenv("WORDS_PER_SECOND", "3.3"))

# --- Aspect Ratio Options ---
ASPECT_RATIOS = {
    "16:9":   {"width": 1280, "height": 720,  "description": "Landscape (YouTube, web)"},
    "9:16":   {"width": 720,  "height": 1280, "description": "Portrait (TikTok, Instagram Reels)"},
}

DEFAULT_ASPECT_RATIO    = "9:16"  # Portrait for social media

# --- Language Detection ---
# Based on research: Confirmed support for English, Chinese, and additional languages
# Note: fal.ai API does NOT have a separate language parameter - language is auto-detected from the prompt
SUPPORTED_LANGUAGES = {
    "en": "English",
    "zh": "Chinese (Simplified)",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ja": "Japanese",
    "ko": "Korean",
    "hi": "Hindi",
    "ar": "Arabic",
    "ru": "Russian",
}

# Note: Language detection is for UI/logging purposes only

# --- App ---
FLASK_PORT              = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG             = os.getenv("FLASK_DEBUG", "false").lower() == "true"
FLASK_SECRET_KEY        = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-prod")
REFERENCE_IMAGE_PATH    = os.getenv("REFERENCE_IMAGE_PATH", "static/images/aira.jpg")
OUTPUT_DIR              = os.getenv("OUTPUT_DIR", "static/outputs")

# --- Supabase (Postgres) ---
# Falls back to local sqlite so `python run.py` still works with zero setup.
DATABASE_URL            = os.getenv("DATABASE_URL", "sqlite:///app.db")
# SQLAlchemy needs "postgresql://" not "postgres://" — Supabase/most providers give the latter.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# --- ImageKit (media storage/CDN) ---
IMAGEKIT_PUBLIC_KEY     = os.getenv("IMAGEKIT_PUBLIC_KEY")
IMAGEKIT_PRIVATE_KEY    = os.getenv("IMAGEKIT_PRIVATE_KEY")
IMAGEKIT_URL_ENDPOINT   = os.getenv("IMAGEKIT_URL_ENDPOINT")
IMAGEKIT_ROOT_FOLDER    = os.getenv("IMAGEKIT_ROOT_FOLDER", "nexchehra")
IMAGEKIT_ENABLED        = bool(IMAGEKIT_PUBLIC_KEY and IMAGEKIT_PRIVATE_KEY and IMAGEKIT_URL_ENDPOINT)

# --- Shot Type Configs ---
# Dimensions are keyed by aspect_ratio so Flux generates the correct image size.
# Kling O3 anchors its video resolution to the input image — portrait image = portrait video.
SHOT_TYPE_CONFIGS = {
    "headshot": {
        "description": "Close-up headshot, face and shoulders only",
        "shot_phrase": "close-up portrait, headshot, face focus, shoulders visible",
        "dimensions": {
            "9:16":  {"flux_width": 768,  "flux_height": 1344},  # portrait
            "16:9": {"flux_width": 1344, "flux_height": 768},   # landscape
            "1:1":  {"flux_width": 1024, "flux_height": 1024},  # square
        },
    },
    "half_body": {
        "description": "Half-body portrait showing upper body and hands",
        "shot_phrase": "half body portrait, upper body shot, waist up",
        "dimensions": {
            "9:16":  {"flux_width": 768,  "flux_height": 1344},  # portrait (TikTok/Reels)
            "16:9": {"flux_width": 1344, "flux_height": 768},   # landscape (YouTube)
            "1:1":  {"flux_width": 1024, "flux_height": 1024},  # square (Instagram)
        },
    },
    "full_body": {
        "description": "Full-body shot from head to toe",
        "shot_phrase": "full body shot, head to toe, entire body visible, standing pose",
        "dimensions": {
            "9:16":  {"flux_width": 768,  "flux_height": 1344},  # portrait (best for full body)
            "16:9": {"flux_width": 1344, "flux_height": 768},   # landscape
            "1:1":  {"flux_width": 1024, "flux_height": 1024},  # square
        },
    },
}

# --- Master Negative Prompt ---
MASTER_NEGATIVE = (
    "deformed face, distorted face, disfigured, ugly, bad anatomy, "
    "extra limbs, extra fingers, extra hands, mutated hands, poorly drawn hands, "
    "poorly drawn face, blurry, low quality, watermark, signature, "
    "six fingers, seven fingers, eight fingers, more than five fingers per hand, "
    "fused fingers, missing fingers, malformed hands, deformed hands, "
    "extra arms, extra legs, mutated limbs, duplicate limbs, "
    "bad proportions, gross proportions, long neck, elongated body, "
    "original clothing, white shirt, old outfit, layered clothing, double clothing, "
    "clothing overlay, printed clothing, text on clothing"
)

def validate():
    """Call on startup to catch missing keys early."""
    missing = []
    if not FAL_KEY or FAL_KEY == "your-fal-api-key-here":
        missing.append("FAL_KEY")
    if not MISTRAL_API_KEY or MISTRAL_API_KEY == "your-mistral-api-key-here":
        missing.append("MISTRAL_API_KEY")
    if missing:
        print(f"⚠️  WARNING: Missing env vars: {', '.join(missing)}")
        print("   Please update your .env file.")
    else:
        print("✓ All environment variables loaded successfully.")
    print(f"✓ Video Model   : Kling O3 Pro (fal-ai/kling-video/o3/pro/image-to-video)")
    print(f"✓ Languages     : {len(SUPPORTED_LANGUAGES)} supported ({', '.join(list(SUPPORTED_LANGUAGES.values())[:3])}, ...)")
    print(f"✓ Video Duration: {VIDEO_DURATION}s | Script: {SCRIPT_MIN_WORDS}–{SCRIPT_MAX_WORDS} words")
    print(f"✓ Aspect Ratios : {', '.join(ASPECT_RATIOS.keys())}")
    print(f"✓ Cost per video: ~${KLING_O3_PRICING['audio_on'] * VIDEO_DURATION:.2f} (Kling O3 Pro + audio)")
    print(f"✓ RAG Model     : {MISTRAL_MODEL}")
    print(f"✓ Knowledge Base: {KNOWLEDGE_BASE_DIR}")
