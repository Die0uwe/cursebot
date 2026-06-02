# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — dashboard.py  v1.0.0
Lichtgewicht Flask web dashboard — draait naast de bot op poort 5000.
Endpoints:
  GET  /           → HTML dashboard
  GET  /api/stats  → JSON stats
  GET  /api/logs   → JSON log buffer
  POST /api/update → Trigger handmatige update check
  POST /api/reset  → Reset CF cache
"""
import os
import sys
import json
import threading
import subprocess
from pathlib import Path
from datetime import datetime, timezone

try:
    from flask import Flask, jsonify, request, send_from_directory
    FLASK_OK = True
except ImportError:
    FLASK_OK = False

from bot.services.stats import STATS

app = Flask(__name__, static_folder="dashboard_static") if FLASK_OK else None

DASHBOARD_HTML = Path(__file__).parent / "dashboard_static" / "index.html"
UPDATER_PATH   = Path(__file__).parent / "updater.py"


@app.route("/")
def index():
    return send_from_directory("dashboard_static", "index.html")


@app.route("/api/stats")
def api_stats():
    return jsonify(STATS.to_dict())


@app.route("/api/logs")
def api_logs():
    return jsonify({"lines": STATS.log_buffer[-100:]})


@app.route("/api/update", methods=["POST"])
def api_update():
    """Trigger handmatige GitHub update check."""
    try:
        result = subprocess.run(
            [sys.executable, str(UPDATER_PATH)],
            capture_output=True, text=True, timeout=30
        )
        updated = result.returncode == 42
        output  = result.stdout.strip()
        STATS.add_log(f"[DASHBOARD] Handmatige update: {'bijgewerkt' if updated else 'up-to-date'}")
        return jsonify({"updated": updated, "output": output})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """Reset de CF file ID cache."""
    try:
        from bot.services.cache import CacheService
        cache = CacheService()
        cache.wipe()
        STATS.add_log("[DASHBOARD] Cache gereset via dashboard")
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/settings", methods=["GET"])
def api_settings_get():
    """Lees huidige instellingen (zonder secrets)."""
    env_path = Path(__file__).parent / ".env"
    settings = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, _, val = line.partition("=")
                # Verberg tokens/keys
                if any(s in key.upper() for s in ["TOKEN", "KEY", "SECRET"]):
                    val = "••••••••"
                settings[key.strip()] = val.strip()
    return jsonify(settings)


@app.route("/api/settings", methods=["POST"])
def api_settings_post():
    """Sla niet-gevoelige instellingen op in .env."""
    ALLOWED = {"CF_AUTHOR_SLUG", "CHECK_INTERVAL_MINUTES",
               "SUMMARIZE_CHANGELOGS", "LOG_LEVEL"}
    data = request.get_json() or {}
    env_path = Path(__file__).parent / ".env"

    if not env_path.exists():
        return jsonify({"error": ".env niet gevonden"}), 404

    lines   = env_path.read_text().splitlines()
    updated = set()

    for i, line in enumerate(lines):
        if "=" in line and not line.strip().startswith("#"):
            key = line.split("=")[0].strip()
            if key in ALLOWED and key in data:
                lines[i] = f"{key}={data[key]}"
                updated.add(key)

    for key in ALLOWED:
        if key in data and key not in updated:
            lines.append(f"{key}={data[key]}")

    env_path.write_text("\n".join(lines) + "\n")
    STATS.add_log(f"[DASHBOARD] Instellingen opgeslagen: {', '.join(updated)}")
    return jsonify({"saved": list(updated)})


def run_dashboard(host: str = "0.0.0.0", port: int = 5000):
    if not FLASK_OK:
        print("[DASHBOARD] Flask niet geïnstalleerd — dashboard uitgeschakeld")
        return
    print(f"[DASHBOARD] Gestart op http://{host}:{port}")
    app.run(host=host, port=port, debug=False, use_reloader=False)


def start_dashboard_thread(port: int = 5000):
    t = threading.Thread(target=run_dashboard, kwargs={"port": port}, daemon=True)
    t.start()
    return t

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: dashboard.py │ Role: Core │ v1.0.0 │ New │ 2026-06-02 15:30║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
