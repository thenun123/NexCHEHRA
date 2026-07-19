"""
test_llm_prompt.py — Tests only the LLM prompt generation.
No Flux, no Kling, no credits used.
Prints the flux_prompt, motion_prompt, video_script, and word count.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Silence Flask/emit_log noise — patch emit_log to just print
import utils
def _quiet_emit(session_id, level, msg):
    prefix = {"processing": "⏳", "success": "✅", "info": "ℹ️ ", "warning": "⚠️ ", "error": "❌"}.get(level, "  ")
    print(f"  {prefix} [{level}] {msg}")
utils.emit_log = _quiet_emit

from generators.llm_generator import LLMGenerator
from clients.flux_client import FluxKontextClient

_sanitizer = FluxKontextClient.__new__(FluxKontextClient)  # instantiate without __init__

# ─── Test cases ───────────────────────────────────────────────────────────────
TEST_CASES = [
    {
        "label": "👗 Fashion outfit + outdoor background",
        "kwargs": {
            "user_description": "Aira in a trendy summer outfit at the beach",
            "gender": "female",
            "body_type": "normal",
            "influencer_name": "Aira",
            "shot_type_pref": "full_body",
        },
    },
    {
        "label": "🏋️ Gym wear + product (protein shake)",
        "kwargs": {
            "user_description": "Aira at the gym promoting a protein shake",
            "product_name": "ProFuel Protein Shake",
            "product_features": "25g protein, zero sugar, chocolate flavour",
            "product_placement": "in_hand",
            "gender": "female",
            "body_type": "normal",
            "influencer_name": "Aira",
            "shot_type_pref": "half_body",
        },
    },
    {
        "label": "🕶️ Casual streetwear + urban background",
        "kwargs": {
            "user_description": "Aira in casual street style in a city setting",
            "gender": "female",
            "body_type": "normal",
            "influencer_name": "Aira",
            "shot_type_pref": "auto",
        },
    },
]

# ─── Run tests ────────────────────────────────────────────────────────────────
SESSION = "test_llm_only"

print("=" * 70)
print("🧪  LLM PROMPT GENERATION TEST  (no Flux / no Kling — zero credits)")
print("=" * 70)

gen = LLMGenerator(SESSION)

for i, tc in enumerate(TEST_CASES, 1):
    print(f"\n{'─' * 70}")
    print(f"TEST {i}: {tc['label']}")
    print(f"{'─' * 70}")

    try:
        result = gen.generate(**tc["kwargs"])

        flux_prompt   = result.get("flux_prompt", "")
        sanitized     = _sanitizer._sanitize_flux_prompt(flux_prompt)
        motion_prompt = result.get("motion_prompt", "")
        video_script  = result.get("video_script", "")
        shot_type     = result.get("shot_type", "")
        word_count    = len(video_script.split())

        print(f"\n📸  FLUX PROMPT — Raw LLM output:")
        print(f"    {flux_prompt}")

        if sanitized != flux_prompt:
            print(f"\n🧹  FLUX PROMPT — After sanitization (what Flux sees):")
            print(f"    {sanitized}")
        else:
            print(f"\n✅  No sanitization needed — LLM output was already clean.")

        print(f"\n🎬  SHOT TYPE : {shot_type}")

        print(f"\n📝  VIDEO SCRIPT ({word_count} words):")
        print(f"    {video_script}")
        
        # ── Punctuation check (to verify new pacing rules) ────────────────
        has_em_dash = "—" in video_script or "--" in video_script
        has_commas = "," in video_script
        if has_em_dash and has_commas:
            print(f"    ✅  PUNCTUATION CHECK: Script uses em-dashes and commas for pacing.")
        else:
            print(f"    ⚠️   PUNCTUATION WARNING: Script might be missing em-dashes (—) or commas for pacing.")

        print(f"\n🎥  RAW MOTION PROMPT ({len(motion_prompt.split())} words):")
        print(f"    {motion_prompt}")
        
        print(f"\n🎬  COMBINED KLING PROMPT (How it gets sent to API):")
        kling_prompt = f'{motion_prompt.rstrip(",. ")}. [Subject, {result.get("voice_tone", "speaks naturally")}]: "{video_script}"'
        print(f"    {kling_prompt}")

        # ── Face safety check (on sanitized prompt — what Flux actually sees) ──
        bad_face_phrases = [
            "same woman", "same man", "same person",
            "preserve face", "preserve exact face",
            "facial structure", "skin tone", "do not alter face",
        ]
        face_leaks = [p for p in bad_face_phrases if p.lower() in sanitized.lower()]

        if face_leaks:
            print(f"\n❌  FACE LEAK in sanitized prompt (bug — should not happen):")
            for leak in face_leaks:
                print(f"    → \"{leak}\"")
        else:
            print(f"\n✅  FACE CHECK PASSED: Flux receives no face descriptions (correct!)")

        # ── Background check ───────────────────────────────────────────────
        bg_keywords = ["background", "studio", "outdoor", "garden", "city", "setting", "scene", "beach", "gym"]
        has_bg = any(kw in flux_prompt.lower() for kw in bg_keywords)
        print(f"{'✅' if has_bg else '⚠️ '} BACKGROUND CHECK: {'background/setting present' if has_bg else 'no background described'}")

        # ── Clothing check ─────────────────────────────────────────────────
        clothing_keywords = ["wearing", "outfit", "dress", "top", "shirt", "jeans", "jacket", "leggings"]
        has_clothing = any(kw in flux_prompt.lower() for kw in clothing_keywords)
        print(f"{'✅' if has_clothing else '⚠️ '} CLOTHING CHECK: {'clothing described' if has_clothing else 'no clothing described'}")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

print(f"\n{'=' * 70}")
print("✅  Test complete — no Flux/Kling credits were used.")
print("=" * 70)
