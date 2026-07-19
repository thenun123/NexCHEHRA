"""
utils/helpers.py — Image encoding and file download helpers
"""

import os
import base64
import requests


# ── Image Helpers ────────────────────────────────────────────

def image_to_data_uri(image_path: str) -> str:
    """Convert a local image file to a base64 data URI."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    ext = os.path.splitext(image_path)[1].lower()
    mime_map = {".png": "image/png", ".webp": "image/webp", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
    mime = mime_map.get(ext, "image/jpeg")
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{data}"


def resolve_image_source(path_or_url: str) -> str:
    """
    fal.ai's image_url params accept either a data URI or a plain https URL.
    Once a file lives on ImageKit we already have a real URL, so just pass it
    through — only fall back to reading + base64-encoding a local file when
    given an actual local path (local dev without ImageKit configured).
    """
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return path_or_url
    return image_to_data_uri(path_or_url)


def download_file(url: str, output_path: str) -> str:
    """Download any file from a URL and save locally."""
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(response.content)
    return output_path
