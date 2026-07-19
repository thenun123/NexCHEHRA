"""
app/main.py — Flask app factory
Creates and configures the Flask application.
"""

import os

from flask import Flask
from flask_cors import CORS

from config import OUTPUT_DIR, DATABASE_URL, FLASK_SECRET_KEY, IMAGEKIT_ENABLED
from app.routes import register_routes
from app.models import db, User, Asset
from app.auth import auth_bp
from flask_login import LoginManager


def create_app() -> Flask:
    """Create and configure the Flask application."""
    # root_path points to the project root (one level up from app/)
    # so that static/, templates/, and send_from_directory all resolve correctly
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    flask_app = Flask(
        __name__,
        static_folder=os.path.join(project_root, "static"),
        template_folder=os.path.join(project_root, "templates"),
        root_path=project_root,
    )
    CORS(flask_app)
    flask_app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB upload limit
    flask_app.config["SECRET_KEY"] = FLASK_SECRET_KEY
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL  # Supabase in prod, sqlite locally
    flask_app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # Supabase's pooler silently drops idle connections — without pre_ping, SQLAlchemy
    # tries to reuse a dead one and crashes with an "Internal Server Error" instead of
    # quietly reconnecting. pool_recycle forces a refresh before the pooler's own cutoff.
    flask_app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }

    db.init_app(flask_app)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(flask_app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with flask_app.app_context():
        db.create_all()

        # Build the static-asset URL map from the Asset table (populated by
        # migrate_static_to_imagekit.py). If ImageKit isn't configured yet
        # (e.g. first-time local dev), this map is just empty and static_url()
        # falls back to serving straight from local /static/.
        static_manifest = {}
        if IMAGEKIT_ENABLED:
            # static_url() is looked up by local_path across ALL categories — templates
            # reference legacy outputs/uploads files directly (e.g. home.html's demo
            # videos, explore.html's sample clips), not just css/js/images.
            for asset in Asset.query.filter(Asset.local_path.isnot(None)).all():
                static_manifest[asset.local_path] = asset.imagekit_url
        flask_app.config["STATIC_MANIFEST"] = static_manifest

    # Only needed for local dev — on Render nothing writes here anymore once
    # ImageKit is wired up (routes.py and the fal.ai clients upload directly).
    if not IMAGEKIT_ENABLED:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        os.makedirs("static/images", exist_ok=True)
        os.makedirs("static/uploads/products", exist_ok=True)
        os.makedirs("static/uploads/references", exist_ok=True)

    def static_url(rel_path: str) -> str:
        """
        Use in templates instead of url_for('static', filename=...).
        Returns the ImageKit CDN URL if this file was migrated, otherwise
        falls back to Flask's normal /static/ route (local dev).
        """
        manifest = flask_app.config.get("STATIC_MANIFEST", {})
        if rel_path in manifest:
            return manifest[rel_path]
        return flask_app.static_url_path + "/" + rel_path.lstrip("/")

    flask_app.jinja_env.globals["static_url"] = static_url

    # Note: static/js/app.js's own hardcoded '/static/images/xxx.png' string
    # literals (persona avatars) get rewritten in-place to ImageKit URLs by
    # migrate_static_to_imagekit.py before that file is uploaded — no
    # separate JS-side lookup needed.

    # Register all route blueprints
    flask_app.register_blueprint(auth_bp)
    register_routes(flask_app)

    return flask_app
