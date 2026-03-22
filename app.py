from flask import Flask, jsonify, render_template, request
from config import APP_NAME, WEB_HOST, WEB_PORT, HEALTH_TOKEN

flask_app = Flask(__name__)
app_started = False
bot_username = "unknown"

@flask_app.route("/")
def home():
    return render_template("welcome.html", app_name=APP_NAME, bot_username=bot_username)

@flask_app.route("/health")
@flask_app.route("/ping")
def health():
    if HEALTH_TOKEN and request.args.get("token") != HEALTH_TOKEN:
        return jsonify({"ok": False, "error": "invalid token"}), 401
    return jsonify({"ok": True, "app": APP_NAME, "bot_username": bot_username, "started": app_started}), 200

@flask_app.route("/status")
def status():
    return jsonify({"ok": True, "app": APP_NAME, "bot_username": bot_username, "started": app_started}), 200

def set_runtime_state(started: bool, username: str):
    global app_started, bot_username
    app_started = started
    bot_username = username or "unknown"

def run_web():
    flask_app.run(host=WEB_HOST, port=WEB_PORT, debug=False, use_reloader=False)
