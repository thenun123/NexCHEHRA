"""
utils/script.py — Script length, duration, and cost calculations
All videos are ALWAYS 15 seconds (Kling O3 Pro).
Scripts must be 38–40 words with strategic punctuation to fill 15 seconds naturally.
"""

from config import (
    KLING_O3_PRICING,
    VIDEO_DURATION,
    SCRIPT_MIN_WORDS,
    SCRIPT_MAX_WORDS,
)


# ── Script / Duration / Cost ─────────────────────────────────

def calculate_duration(script: str) -> int:
    """
    Always returns 15. Every video in this app is exactly 15 seconds (Kling O3 Pro).
    Scripts must be 38–40 words with punctuation (em-dashes, commas) to pace the AI voice perfectly.
    """
    return VIDEO_DURATION  # always 15


def calculate_cost(duration: int = None, mode: str = None) -> float:
    """
    Return video generation cost in USD. Duration is always 15s (Kling O3 Pro).
    audio_on  → $0.168/s  (generate_audio=True, default)
    audio_off → $0.112/s  (generate_audio=False, silent)
    """
    duration = VIDEO_DURATION  # ignore arg — always 15
    cost_mode = "audio_off" if mode == "audio_off" else "audio_on"
    return round(KLING_O3_PRICING[cost_mode] * duration, 2)


def enforce_script_length(script: str) -> tuple[str, list[str]]:
    """
    Enforce 38–40 word script for a 15-second video.
    Returns (final_script, list_of_warnings).
    - Over 40 words → trimmed to 40
    - Under 38 words → returned as-is with a warning
    """
    warnings = []
    words = script.strip().split()
    word_count = len(words)

    if word_count > SCRIPT_MAX_WORDS:
        trimmed = " ".join(words[:SCRIPT_MAX_WORDS])
        script = trimmed.rstrip(",") + "."
        warnings.append(f"Script trimmed from {word_count} to {SCRIPT_MAX_WORDS} words.")

    elif word_count < SCRIPT_MIN_WORDS:
        warnings.append(
            f"Script is only {word_count} words (minimum {SCRIPT_MIN_WORDS} for 15s video). "
            f"Consider adding more content."
        )

    return script, warnings


def trim_script(script: str, max_words: int = None) -> str:
    """
    Backward-compatible trim. Always enforces SCRIPT_MAX_WORDS.
    """
    script, _ = enforce_script_length(script)
    return script
