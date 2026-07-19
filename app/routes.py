"""
app/routes.py — All Flask route handlers
Organized into sections: Frontend, SSE, Uploads, Pipeline Phases, Cost Preview
"""

import os
import json
import time
import queue
import uuid

from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, url_for
from flask_login import login_required

from config import (
    FLASK_PORT,
    FLASK_DEBUG,
    OUTPUT_DIR,
    SUPPORTED_LANGUAGES,
    PRODUCT_PLACEMENTS,
    SHOT_TYPE_CONFIGS,
)
from utils import (
    emit_log, create_session, cleanup_session, log_queues,
    calculate_duration, calculate_cost, trim_script,
)
from generators import LLMGenerator
from clients import FluxKontextClient, KlingClient
from clients.imagekit_client import persist_bytes
from flask_login import current_user


def register_routes(app: Flask):
    """Register all route handlers on the Flask app."""

    # ── Serve Frontend ───────────────────────────────────────────
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/home")
    @login_required
    def home():
        return render_template("home.html")

    @app.route("/dashboard")
    @login_required
    def dashboard():
        return redirect(url_for('home'))

    @app.route("/explore")
    @login_required
    def explore():
        return render_template("explore.html")

    @app.route("/influencer")
    @login_required
    def influencer():
        return render_template("influencer.html")

    @app.route("/video")
    @login_required
    def video():
        return render_template("video.html")



    @app.route("/profile")
    @login_required
    def profile():
        return render_template("profile.html")

    @app.route("/history")
    @login_required
    def history():
        return render_template("history.html")

    @app.route("/settings")
    @login_required
    def settings():
        return render_template("settings.html")

    @app.route("/static/<path:path>")
    def serve_static(path):
        return send_from_directory("static", path)

    # ── SSE Log Stream ───────────────────────────────────────────
    @app.route("/api/logs/<session_id>")
    def get_logs(session_id):
        """Server-Sent Events endpoint — streams real-time logs to frontend."""
        def stream():
            if session_id not in log_queues:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Invalid session'})}\n\n"
                return
            while True:
                try:
                    log = log_queues[session_id].get(timeout=1)
                    yield f"data: {json.dumps(log)}\n\n"
                    if log.get("type") == "complete":
                        break
                except queue.Empty:
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
            # Session consumed — free memory
            cleanup_session(session_id)

        return app.response_class(stream(), mimetype="text/event-stream")

    # ── Product Upload ───────────────────────────────────────────
    @app.route("/api/upload_product", methods=["POST"])
    @login_required
    def upload_product():
        """Upload a product image. Returns saved path for use in Phase 1."""
        if "product_image" not in request.files:
            return jsonify({"status": "error", "message": "No file uploaded"}), 400

        file = request.files["product_image"]
        if file.filename == "":
            return jsonify({"status": "error", "message": "Empty filename"}), 400

        # Validate file type
        allowed = {".jpg", ".jpeg", ".png", ".webp"}
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed:
            return jsonify({"status": "error", "message": f"Invalid file type. Allowed: {', '.join(allowed)}"}), 400

        # Persist to ImageKit (falls back to local static/uploads if ImageKit isn't configured)
        filename = f"product_{uuid.uuid4().hex[:8]}{ext}"
        url = persist_bytes(
            file.read(), filename, subfolder="uploads/products",
            category="upload", subtype="product",
            user_id=getattr(current_user, "id", None),
        )

        return jsonify({
            "status": "success",
            "product_path": url,
            "product_url": url,
        })

    # ── Custom Reference Upload ──────────────────────────────────────
    @app.route("/api/upload_reference", methods=["POST"])
    @login_required
    def upload_reference():
        """Upload a custom reference image. Returns saved path for use in Phase 1."""
        if "reference_image" not in request.files:
            return jsonify({"status": "error", "message": "No file uploaded"}), 400

        file = request.files["reference_image"]
        if file.filename == "":
            return jsonify({"status": "error", "message": "Empty filename"}), 400

        # Validate file type
        allowed = {".jpg", ".jpeg", ".png", ".webp"}
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed:
            return jsonify({"status": "error", "message": f"Invalid file type. Allowed: {', '.join(allowed)}"}), 400

        # Persist to ImageKit (falls back to local static/uploads if ImageKit isn't configured)
        filename = f"ref_{uuid.uuid4().hex[:8]}{ext}"
        url = persist_bytes(
            file.read(), filename, subfolder="uploads/references",
            category="upload", subtype="reference",
            user_id=getattr(current_user, "id", None),
        )

        return jsonify({
            "status": "success",
            "ref_path": url,
            "ref_url": url,
        })

    # ── Supported Languages ──────────────────────────────────────────
    @app.route("/api/languages", methods=["GET"])
    def get_languages():
        """Returns the list of supported script languages for Kling."""
        return jsonify(SUPPORTED_LANGUAGES)

    # ── Phase 0: LLM ─────────────────────────────────────────────
    @app.route("/api/phase0", methods=["POST"])
    @login_required
    def phase0():
        """
        LLM analyzes user description.
        Returns: flux_prompt, motion_prompt, video_script, shot_type, duration, cost estimate
        Supports optional product context and multi-language script generation.
        """
        data        = request.json
        session_id  = data.get("session_id", f"s_{int(time.time())}")
        description = data.get("description", "")
        script      = data.get("script", "")
        shot_pref   = data.get("shot_type", "auto")

        # Influencer metadata
        gender          = data.get("gender", "unknown")
        body_type       = data.get("body_type", "normal")
        influencer_name = data.get("influencer_name", "Aira")

        # Language selection (NEW)
        script_language = data.get("script_language", "en")

        # Product fields (optional)
        product_name      = data.get("product_name") or None
        product_features  = data.get("product_features") or None
        product_placement = data.get("product_placement") or None
        has_product       = data.get("has_product", False)

        # Clear product fields if toggle is off
        if not has_product:
            product_name = None
            product_features = None
            product_placement = None

        create_session(session_id)
        emit_log(session_id, "info", "🚀 Phase 0: Starting LLM analysis...")
        if has_product and product_name:
            emit_log(session_id, "info", f"🛍️ Product mode: {product_name} ({product_placement})")

        try:
            llm     = LLMGenerator(session_id)
            prompts = llm.generate(description, script or None, shot_pref,
                                   product_name=product_name, product_features=product_features,
                                   product_placement=product_placement,
                                   gender=gender, body_type=body_type, influencer_name=influencer_name,
                                   script_language=script_language)  # NEW: Pass language
            llm.cleanup()

            duration    = prompts["duration"]  # Will be 15
            cost        = calculate_cost(duration, "audio_on")  # Kling O3 Pro with audio

            # Log the generated script language
            language_name = SUPPORTED_LANGUAGES.get(script_language, "English")
            emit_log(session_id, "success", f"✓ Script generated in {language_name}")

            emit_log(session_id, "success", "✓ Phase 0 complete — review your prompts")
            emit_log(session_id, "complete", json.dumps({"phase": 0}))

            return jsonify({
                "status":       "success",
                "session_id":   session_id,
                "shot_type":    prompts["shot_type"],
                "flux_prompt":  prompts["flux_prompt"],
                "motion_prompt":prompts["motion_prompt"],
                "voice_tone":   prompts.get("voice_tone", "speaks enthusiastically and naturally"),
                "video_script": prompts["video_script"],
                "duration":     duration,
                "cost_estimate":cost,
                "cost_mode":    "Kling O3 Pro",
                "influencer_name": prompts["influencer_name"],
                "technical_reasoning": prompts.get("technical_reasoning", ""),
                "product_name":      product_name,
                "product_placement": product_placement,
                "has_product":       has_product,
                "script_language":   script_language,
            })

        except Exception as e:
            emit_log(session_id, "error", f"❌ Phase 0 failed: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    # ── Phase 1: Flux Kontext ────────────────────────────────────
    @app.route("/api/phase1", methods=["POST"])
    @login_required
    def phase1():
        """
        Flux Kontext generates styled portrait from reference image.
        Optionally composites a product image using the Multi endpoint.
        """
        data         = request.json
        session_id   = data.get("session_id", f"s_{int(time.time())}")
        flux_prompt  = data.get("flux_prompt", "")
        shot_type    = data.get("shot_type", "half_body")
        aspect_ratio = data.get("aspect_ratio", "9:16")

        # Custom reference image (optional — overrides default)
        reference_image_path = data.get("reference_image_path") or None
        gender               = data.get("gender", "unknown")
        body_type            = data.get("body_type", "normal")

        # Product fields (optional)
        product_image_path = data.get("product_image_path") or None
        product_placement  = data.get("product_placement") or None

        shot_config = SHOT_TYPE_CONFIGS.get(shot_type, SHOT_TYPE_CONFIGS["half_body"])

        if session_id not in log_queues:
            create_session(session_id)

        emit_log(session_id, "info", "🎨 Phase 1: Generating portrait with Flux Kontext Max...")
        if reference_image_path:
            emit_log(session_id, "info", f"📸 Using custom reference: {reference_image_path}")
        if product_image_path:
            emit_log(session_id, "info", f"🛍️ Product image included: {product_image_path}")

        try:
            # Guard: verify product image still exists before sending to Flux
            # (product_image_path is an ImageKit URL when ImageKit is configured, a local path otherwise)
            product_is_url = bool(product_image_path) and product_image_path.startswith(("http://", "https://"))
            if product_image_path and not product_is_url and not os.path.exists(product_image_path):
                emit_log(session_id, "error", f"Product image not found: {product_image_path}")
                return jsonify({"status": "error", "message": f"Product image not found: {product_image_path}"}), 400

            flux = FluxKontextClient(session_id)
            save_path, image_url = flux.generate(
                flux_prompt, shot_config, session_id,
                product_image_path=product_image_path,
                product_placement=product_placement,
                reference_image_path=reference_image_path,
                gender=gender,
                body_type=body_type,
                aspect_ratio=aspect_ratio,
            )

            # Web-accessible path (save_path is already a full ImageKit URL when ImageKit is
            # configured; only local dev fallback paths need the leading "/" for Flask's /static/ route)
            web_path = save_path if save_path.startswith(("http://", "https://")) else "/" + save_path.replace("\\", "/")

            emit_log(session_id, "complete", json.dumps({"phase": 1}))

            return jsonify({
                "status":       "success",
                "session_id":   session_id,
                "portrait_path": web_path,
                "portrait_local_path": save_path,  # local FS path for Phase 2 (CDN-safe)
                "portrait_url": image_url,
            })

        except Exception as e:
            emit_log(session_id, "error", f"❌ Phase 1 failed: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    # ── Phase 2: Kling O3 Pro ─────────────────────────────────────
    @app.route("/api/phase2", methods=["POST"])
    @login_required
    def phase2():
        """
        Kling O3 Pro generates video from portrait + motion prompt + voice_tone + script.
        Returns: video file path.
        Uses fal-ai/kling-video/o3/pro/image-to-video endpoint.
        """
        data           = request.json
        session_id     = data.get("session_id", f"s_{int(time.time())}")
        portrait_path  = data.get("portrait_local_path", "")
        portrait_url   = data.get("portrait_url", "")
        motion_prompt  = data.get("motion_prompt", "person talking naturally, subtle head movement")
        video_script   = data.get("video_script", "")
        voice_tone     = data.get("voice_tone", "speaks enthusiastically and naturally")
        product_name   = data.get("product_name") or None   # preserved in casing; rest of script lowercased
        duration       = int(data.get("duration", 15))  # Default 15 seconds (Kling O3 max)
        aspect_ratio   = data.get("aspect_ratio", "9:16")  # Kept for API compat (O3 ignores it)

        # Prefer the persisted ImageKit URL / local path over fal.ai's short-lived temp URL
        portrait_is_usable = bool(portrait_path) and (
            portrait_path.startswith(("http://", "https://")) or os.path.exists(portrait_path)
        )
        image_source = portrait_path if portrait_is_usable else portrait_url
        if not image_source:
            return jsonify({"status": "error", "message": "No portrait image provided"}), 400

        # Safety trim (now for 15 seconds)
        video_script = trim_script(video_script)
        duration     = calculate_duration(video_script)  # Returns 15

        if session_id not in log_queues:
            create_session(session_id)

        emit_log(session_id, "info", "🎬 Using Kling O3 Pro for video generation")
        emit_log(session_id, "info", f"🎭 Voice tone: {voice_tone}")

        try:
            kling = KlingClient(session_id)
            save_path, video_url = kling.generate(
                image_url      = image_source,
                motion_prompt  = motion_prompt,
                video_script   = video_script,
                duration       = duration,
                voice_tone     = voice_tone,
                session_id     = session_id,
                aspect_ratio   = aspect_ratio,
                product_name   = product_name,
            )

            # Calculate Kling O3 Pro cost
            cost = calculate_cost(duration, "audio_on")

            web_path = save_path if save_path.startswith(("http://", "https://")) else "/" + save_path.replace("\\", "/")

            emit_log(session_id, "success", "🎉 All phases complete!")
            emit_log(session_id, "complete", json.dumps({"phase": 2}))

            return jsonify({
                "status":     "success",
                "session_id": session_id,
                "video_path": web_path,
                "video_url":  video_url,
                "duration":   duration,
                "final_cost": cost,
            })

        except Exception as e:
            emit_log(session_id, "error", f"❌ Phase 2 failed: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    # ── Cost Preview (no API call) ────────────────────────────────
    @app.route("/api/cost_preview", methods=["POST"])
    def cost_preview():
        """
        Lightweight endpoint — just calculates cost from script.
        Always returns Kling O3 Pro pricing (~$2.52 for 15s with audio).
        """
        data     = request.json
        script   = data.get("script", "")
        duration = calculate_duration(script)  # Always 15
        cost     = calculate_cost(duration, "audio_on")

        return jsonify({
            "duration":     duration,
            "words":        len(script.split()),
            "current_mode": "Kling O3 Pro",
            "current_cost": cost,
        })

    # ── RAG Chatbot ──────────────────────────────────────────────
    # Lazy-loaded singleton so knowledge base is only indexed once
    _assistant_cache = {}

    @app.route("/api/chat", methods=["POST"])
    def chat():
        """
        RAG chatbot endpoint.
        Accepts: {"message": "user question"}
        Returns: {"reply": "assistant answer"}
        """
        from utils.rag_engine import NexAssistant

        # Initialize assistant once (lazy singleton)
        if "assistant" not in _assistant_cache:
            try:
                _assistant_cache["assistant"] = NexAssistant()
            except Exception as e:
                return jsonify({
                    "reply": f"Sorry, the assistant failed to initialize. ({str(e)[:100]})"
                }), 500

        data = request.json
        message = (data.get("message") or "").strip()

        if not message:
            return jsonify({"reply": "Please type a message to get help! 😊"}), 400

        try:
            assistant = _assistant_cache["assistant"]
            reply = assistant.ask(message)
            return jsonify({"reply": reply})
        except Exception as e:
            return jsonify({
                "reply": f"Sorry, something went wrong. Please try again. ({str(e)[:100]})"
            }), 500

