"""
clients/imagekit_client.py — thin wrapper around the ImageKit SDK.

Every file NexCHEHRA touches (site assets, user uploads, AI-generated
images/videos) goes through this module so there's exactly one place that
knows how to talk to ImageKit.

If IMAGEKIT_ENABLED is False (keys missing), upload_* functions raise —
callers should check config.IMAGEKIT_ENABLED before relying on this in
production. Local dev without keys still works because app/main.py falls
back to serving straight from /static in that case.

Built against imagekitio SDK v5.x (client.files.upload(...) — a private_key-
only REST client; it does NOT need public_key/url_endpoint to make calls,
the CDN URL for each file comes back directly in the upload response).
"""
import requests
import os
import mimetypes
from imagekitio import ImageKit

from config import (
    IMAGEKIT_PRIVATE_KEY,
    IMAGEKIT_ROOT_FOLDER,
    IMAGEKIT_ENABLED,
)

_client = None


def get_client() -> ImageKit:
    global _client
    if _client is None:
        if not IMAGEKIT_ENABLED:
            raise RuntimeError(
                "ImageKit is not configured — set IMAGEKIT_PUBLIC_KEY, "
                "IMAGEKIT_PRIVATE_KEY, IMAGEKIT_URL_ENDPOINT in your env."
            )
        _client = ImageKit(private_key=IMAGEKIT_PRIVATE_KEY)
    return _client


def _folder(subfolder: str = "") -> str:
    """Build the ImageKit folder path, rooted under IMAGEKIT_ROOT_FOLDER."""
    subfolder = subfolder.strip("/")
    return f"/{IMAGEKIT_ROOT_FOLDER}/{subfolder}".rstrip("/")


def upload_bytes(data: bytes, file_name: str, subfolder: str = "") -> dict:
    """Upload raw bytes (e.g. a Flask request.files upload). Returns {url, file_id, name}."""
    ik = get_client()
    result = ik.files.upload(
        file=data,
        file_name=file_name,
        folder=_folder(subfolder),
        use_unique_file_name=True,
    )
    return {"url": result.url, "file_id": result.file_id, "name": result.name}


def upload_local_file(local_path: str, subfolder: str = "", file_name: str = None) -> dict:
    """Upload a file already on disk. Returns {url, file_id, name}."""
    file_name = file_name or os.path.basename(local_path)
    with open(local_path, "rb") as f:
        return upload_bytes(f.read(), file_name, subfolder)


def upload_from_url(source_url: str, file_name: str, subfolder: str = "") -> dict:
    """
    Fetch a remote file (e.g. fal.ai's temporary output URL) into memory and
    upload it to ImageKit. Never touches local disk.

    Note: the installed imagekitio SDK (v5.x) only accepts bytes/file-like
    objects for `file=`, not a plain URL string, even though ImageKit's REST
    API itself supports server-side URL fetch — so we download here instead.
    Returns {url, file_id, name}.
    """
    resp = requests.get(source_url, timeout=60)
    resp.raise_for_status()
    return upload_bytes(resp.content, file_name, subfolder)


def guess_content_type(file_name: str) -> str:
    return mimetypes.guess_type(file_name)[0] or "application/octet-stream"


def persist_from_url(source_url: str, file_name: str, subfolder: str, category: str,
                      subtype: str = None, session_id: str = None, user_id: int = None) -> str:
    """
    Used by flux_client.py / kling_client.py right after fal.ai returns a
    generated image/video URL. Uploads it to ImageKit (fetched server-side
    from fal.ai's temporary URL, never touches local disk) and records an
    Asset row. Returns the ImageKit URL — callers use this exactly like they
    used to use the old local save_path.

    Falls back to the legacy local-download behaviour if ImageKit isn't
    configured, so `python run.py` still works with zero setup locally.
    """
    if not IMAGEKIT_ENABLED:
        from utils.helpers import download_file
        local_path = os.path.join("static", "outputs", file_name)
        download_file(source_url, local_path)
        return local_path

    from app.models import db, Asset
    result = upload_from_url(source_url, file_name, subfolder=subfolder)
    asset = Asset(
        category=category,
        subtype=subtype,
        local_path=None,
        imagekit_url=result["url"],
        imagekit_file_id=result["file_id"],
        session_id=session_id,
        user_id=user_id,
    )
    db.session.add(asset)
    db.session.commit()
    return result["url"]


def persist_bytes(data: bytes, file_name: str, subfolder: str, category: str,
                   subtype: str = None, session_id: str = None, user_id: int = None) -> str:
    """Same as persist_from_url but for raw bytes (e.g. a Flask request.files upload)."""
    if not IMAGEKIT_ENABLED:
        local_path = os.path.join("static", "uploads", subfolder, file_name)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(data)
        return local_path

    from app.models import db, Asset
    result = upload_bytes(data, file_name, subfolder=subfolder)
    asset = Asset(
        category=category,
        subtype=subtype,
        local_path=None,
        imagekit_url=result["url"],
        imagekit_file_id=result["file_id"],
        session_id=session_id,
        user_id=user_id,
    )
    db.session.add(asset)
    db.session.commit()
    return result["url"]
