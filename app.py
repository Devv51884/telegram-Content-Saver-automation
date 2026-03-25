from __future__ import annotations

import os
from datetime import datetime, timezone
from flask import Flask, jsonify, render_template, request

from config import APP_NAME, WEB_HOST, WEB_PORT, HEALTH_TOKEN

flask_app = Flask(__name__)

# Runtime state shared with main/bot startup
app_started = False
bot_username = "unknown"
bot_started_at = None
last_error = None
startup_mode = "unknown"
version = os.getenv("APP_VERSION", "v12")


@flask_app.route("/")
def home():
    try:
        return render_template(
            "welcome.html",
            app_name=APP_NAME,
            bot_username=bot_username,
            started=app_started,
            version=version,
        )
    except Exception:
        status = "running" if app_started else "starting"
        return f"{APP_NAME} {version} is {status} 🚀"


def _authorized() -> bool:
    if not HEALTH_TOKEN:
        return True
    token = request.args.get("token", "")
    return token == HEALTH_TOKEN


def _runtime_payload() -> dict:
    return {
        "ok": True,
        "app": APP_NAME,
        "version": version,
        "bot_username": bot_username,
        "started": app_started,
        "startup_mode": startup_mode,
        "started_at": bot_started_at,
        "last_error": last_error,
        "server_time_utc": datetime.now(timezone.utc).isoformat(),
    }


@flask_app.route("/health")
@flask_app.route("/ping")
def health():
    if not _authorized():
        return jsonify({"ok": False, "error": "invalid token"}), 401

    code = 200 if app_started else 503
    return jsonify(_runtime_payload()), code


@flask_app.route("/status")
def status():
    if not _authorized():
        return jsonify({"ok": False, "error": "invalid token"}), 401
    return jsonify(_runtime_payload()), 200


@flask_app.route("/ready")
def ready():
    if not _authorized():
        return jsonify({"ok": False, "error": "invalid token"}), 401
    return jsonify({"ok": app_started, "ready": app_started}), (200 if app_started else 503)


@flask_app.route("/runtime")
def runtime():
    if not _authorized():
        return jsonify({"ok": False, "error": "invalid token"}), 401
    return jsonify(_runtime_payload()), 200


def set_runtime_state(
    started: bool,
    username: str | None = None,
    error: str | None = None,
    mode: str | None = None,
):
    global app_started, bot_username, bot_started_at, last_error, startup_mode

    app_started = started
    bot_username = username or bot_username or "unknown"
    last_error = error
    if mode:
        startup_mode = mode

    if started:
        bot_started_at = datetime.now(timezone.utc).isoformat()
    elif not bot_started_at:
        bot_started_at = None


def run_web():
    print(f"🌐 Web server running on {WEB_HOST}:{WEB_PORT}")
    flask_app.run(
        host=WEB_HOST,
        port=WEB_PORT,
        debug=False,
        use_reloader=False,
        threaded=True,
    )
