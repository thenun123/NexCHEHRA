"""
migrate_static_to_imagekit.py — one-time migration.

Uploads EVERY file under static/ (assets, css, images, js, outputs, uploads,
vedio — all subfolders, nothing skipped) to ImageKit, preserving the exact
folder structure. Records every uploaded file as an Asset row so the app can
look up ImageKit URLs by local path afterwards, instead of reading disk.

Two passes, because css/js reference other static files internally:
  Pass 1 — upload every non-text asset (images, video, fonts, etc). Build a
           {relative_path: imagekit_url} map.
  Pass 2 — for .css/.js files, rewrite any '/static/<path>' or
           'static/<path>' reference found in the file content to the
           matching ImageKit URL from pass 1, THEN upload the patched
           content (not the original bytes).

Run this once, locally, before your first Render deploy:
    python migrate_static_to_imagekit.py

Safe to re-run — it skips any local_path that already has an Asset row
unless you pass --force.
"""

import os
import re
import sys
import argparse

from app import create_app
from app.models import db, Asset
from clients import imagekit_client
from config import IMAGEKIT_ENABLED

STATIC_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

TEXT_EXTS = {".css", ".js"}
SKIP_NAMES = {".DS_Store"}

# category by top-level subfolder under static/
CATEGORY_BY_PREFIX = {
    "outputs": "output",
    "uploads": "upload",
}


def category_for(rel_path: str) -> str:
    top = rel_path.split("/")[0]
    return CATEGORY_BY_PREFIX.get(top, "static")


def iter_static_files():
    for dirpath, _, filenames in os.walk(STATIC_ROOT):
        for name in filenames:
            if name in SKIP_NAMES:
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, STATIC_ROOT).replace(os.sep, "/")
            yield full, rel


def patch_references(content: str, url_map: dict) -> str:
    """Rewrite /static/x/y or static/x/y references to their ImageKit URL."""
    def _sub(match):
        rel = match.group(1)
        return url_map.get(rel, match.group(0))

    # matches url(/static/foo/bar.png), url('static/foo/bar.png'), "/static/foo/bar.png", etc.
    pattern = re.compile(r"[\"'(]?/?static/([A-Za-z0-9_\-./]+)")

    def _sub2(m):
        rel = m.group(1)
        if rel in url_map:
            prefix = m.group(0)[0] if m.group(0)[0] in "\"'(" else ""
            return f"{prefix}{url_map[rel]}"
        return m.group(0)

    return pattern.sub(_sub2, content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Re-upload even if an Asset row already exists")
    args = parser.parse_args()

    if not IMAGEKIT_ENABLED:
        print("✗ IMAGEKIT_PUBLIC_KEY / IMAGEKIT_PRIVATE_KEY / IMAGEKIT_URL_ENDPOINT not set. Aborting.")
        sys.exit(1)

    app = create_app()
    with app.app_context():
        existing_paths = {a.local_path for a in Asset.query.all()}

        all_files = list(iter_static_files())
        print(f"Found {len(all_files)} files under static/")

        binary_files = [(f, r) for f, r in all_files if os.path.splitext(r)[1].lower() not in TEXT_EXTS]
        text_files   = [(f, r) for f, r in all_files if os.path.splitext(r)[1].lower() in TEXT_EXTS]

        url_map = {}

        # ── Pass 1: binary/media files ──────────────────────────────
        print(f"\n[Pass 1] Uploading {len(binary_files)} binary files (images, video, fonts, uploads, outputs)...")
        for i, (full, rel) in enumerate(binary_files, 1):
            if rel in existing_paths and not args.force:
                existing_asset = Asset.query.filter_by(local_path=rel).first()
                url_map[rel] = existing_asset.imagekit_url
                continue
            try:
                subfolder = os.path.dirname(rel)  # mirrors folder structure in ImageKit
                result = imagekit_client.upload_local_file(full, subfolder=subfolder, file_name=os.path.basename(rel))
                url_map[rel] = result["url"]
                asset = Asset.query.filter_by(local_path=rel).first() or Asset(local_path=rel)
                asset.category = category_for(rel)
                asset.subtype = os.path.dirname(rel).split("/")[-1] if "/" in rel else None
                asset.imagekit_url = result["url"]
                asset.imagekit_file_id = result["file_id"]
                db.session.add(asset)
                db.session.commit()
                print(f"  [{i}/{len(binary_files)}] {rel} -> {result['url']}")
            except Exception as e:
                print(f"  ✗ FAILED {rel}: {e}")

        # ── Pass 2: css/js, with references patched to Pass 1 URLs ──
        print(f"\n[Pass 2] Patching + uploading {len(text_files)} css/js files...")
        for i, (full, rel) in enumerate(text_files, 1):
            if rel in existing_paths and not args.force:
                continue
            try:
                with open(full, "r", encoding="utf-8") as f:
                    content = f.read()
                patched = patch_references(content, url_map)
                subfolder = os.path.dirname(rel)
                result = imagekit_client.upload_bytes(
                    patched.encode("utf-8"), os.path.basename(rel), subfolder=subfolder
                )
                url_map[rel] = result["url"]
                asset = Asset.query.filter_by(local_path=rel).first() or Asset(local_path=rel)
                asset.category = "static"
                asset.imagekit_url = result["url"]
                asset.imagekit_file_id = result["file_id"]
                db.session.add(asset)
                db.session.commit()
                print(f"  [{i}/{len(text_files)}] {rel} -> {result['url']}")
            except Exception as e:
                print(f"  ✗ FAILED {rel}: {e}")

        print(f"\nDone. {len(url_map)} files mirrored to ImageKit and recorded in the Asset table.")
        print("The app reads this table at startup to build its static_url() lookup — no code changes needed per-deploy.")


if __name__ == "__main__":
    main()
