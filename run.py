"""
run.py — Entry point for the AI Influencer Video Generator
Usage: python run.py
"""

import config
from config import FLASK_PORT, FLASK_DEBUG
from app import create_app

app = create_app()

if __name__ == "__main__":
    print("=" * 65)
    print("🎬  AI Influencer Video Generator")
    print("=" * 65)
    config.validate()
    print(f"\n✓ Server starting → http://localhost:{FLASK_PORT}")
    print(f"✓ Flux Model  : {config.FLUX_MODEL}")
    print(f"✓ Flux Multi  : {config.FLUX_MULTI_MODEL} (product placement)")
    print(f"✓ Kling Model : {config.KLING_MODEL}")
    print(f"✓ Voices      : {len(config.KLING_LANGUAGES)} available")
    print(f"✓ Reference   : {config.REFERENCE_IMAGE_PATH}")
    print(f"✓ Products    : {', '.join(config.PRODUCT_PLACEMENTS.keys())}")
    print("=" * 65)
    app.run(debug=FLASK_DEBUG, port=FLASK_PORT, threaded=True)
