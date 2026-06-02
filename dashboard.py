# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""CurseBot — dashboard.py v2.0.0 — Flask API backend voor het web dashboard."""
import sys
import json
import threading
import subprocess
from pathlib import Path

try:
    from flask import Flask, jsonify, request, send_from_directory
    from flask_cors import CORS
    FLASK_OK = True
except ImportError:
    try:
        from flask import Flask, jsonify, request, send_from_directory
        FLASK_OK = True
    except ImportError:
        FLASK_OK = False

from bot.services.stats import STATS

app  = Flask(__name__, static_folder="dashboard_static") if FLASK_OK else None
BASE = Path(__file__).parent

if FLASK_OK and app:
    try:
        from flask_cors import CORS
        CORS(app)
    except ImportError:
        pass

# ── Statische files ────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("dashboard_static", "index.html")

# ── Stats API ──────────────────────────────────────────────────────────────────
@app.route("/api/stats")
def api_stats():
    data = STATS.to_dict()
    # Voeg project details toe als beschikbaar
    data["projects"] = [
        {"id": p.id, "name": p.name, "slug": p.slug,
         "url": p.url, "downloads": p.downloads,
         "logo_url": p.logo_url, "summary": p.summary}
        for p in STATS.project_list
    ] if hasattr(STATS, "project_list") else []
    return jsonify(data)

@app.route("/api/logs")
def api_logs():
    return jsonify({"lines": STATS.log_buffer[-100:]})

# ── Acties API ─────────────────────────────────────────────────────────────────
@app.route("/api/update", methods=["POST"])
def api_update():
    try:
        result = subprocess.run(
            [sys.executable, str(BASE / "updater.py")],
            capture_output=True, text=True, timeout=60
        )
        updated = result.returncode == 42
        STATS.add_log(f"[DASHBOARD] Update: {'bijgewerkt' if updated else 'up-to-date'}")
        return jsonify({"updated": updated, "output": result.stdout.strip()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/reset", methods=["POST"])
def api_reset():
    try:
        from bot.services.cache import CacheService
        CacheService().wipe()
        STATS.add_log("[DASHBOARD] Cache gereset")
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/check", methods=["POST"])
def api_check():
    """Trigger een handmatige CF check via de cog."""
    try:
        STATS.add_log("[DASHBOARD] Handmatige check getriggerd")
        # Zet een flag die de cog oppikt
        STATS.force_check = True
        return jsonify({"ok": True, "message": "Check getriggerd"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Settings API ───────────────────────────────────────────────────────────────
ALLOWED_SETTINGS = {
    "CF_AUTHOR_SLUG", "CF_AUTHOR_ID",
    "CHECK_INTERVAL_MINUTES", "SUMMARIZE_CHANGELOGS", "LOG_LEVEL"
}

@app.route("/api/settings", methods=["GET"])
def api_settings_get():
    env_path = BASE / ".env"
    settings = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                k = k.strip()
                if any(s in k.upper() for s in ["TOKEN", "KEY", "SECRET"]):
                    v = "••••••••"
                settings[k] = v.strip()
    return jsonify(settings)

@app.route("/api/settings", methods=["POST"])
def api_settings_post():
    data     = request.get_json() or {}
    env_path = BASE / ".env"
    if not env_path.exists():
        return jsonify({"error": ".env niet gevonden"}), 404
    lines   = env_path.read_text().splitlines()
    updated = set()
    for i, line in enumerate(lines):
        if "=" in line and not line.strip().startswith("#"):
            k = line.split("=")[0].strip()
            if k in ALLOWED_SETTINGS and k in data:
                lines[i] = f"{k}={data[k]}"
                updated.add(k)
    for k in ALLOWED_SETTINGS:
        if k in data and k not in updated:
            lines.append(f"{k}={data[k]}")
    env_path.write_text("\n".join(lines) + "\n")
    STATS.add_log(f"[DASHBOARD] Instellingen opgeslagen: {', '.join(updated)}")
    return jsonify({"saved": list(updated)})

# ── Server ─────────────────────────────────────────────────────────────────────

@app.route("/api/watchlist", methods=["GET"])
def api_watchlist_get():
    """Alle watchlist items — voor de UI."""
    try:
        from bot.services.cache import CacheService
        cache = CacheService()
        guild_id = request.args.get("guild_id", "0")
        items = cache.watchlist_get(guild_id) if guild_id != "0" else cache.watchlist_all()
        return jsonify({"items": items, "count": len(items)})
    except Exception as e:
        return jsonify({"items": [], "count": 0, "error": str(e)})

@app.route("/api/watchlist/add", methods=["POST"])
def api_watchlist_add():
    """Voeg addon toe via UI — zoekt op ID of naam."""
    data     = request.get_json() or {}
    guild_id = data.get("guild_id", "0")
    addon_id = data.get("addon_id")
    name     = data.get("addon_name", "Onbekend")
    if not addon_id:
        return jsonify({"error": "addon_id vereist"}), 400
    try:
        from bot.services.cache import CacheService
        cache = CacheService()
        added = cache.watchlist_add(
            guild_id=guild_id,
            addon_id=int(addon_id),
            addon_name=data.get("addon_name",""),
            addon_slug=data.get("addon_slug",""),
            addon_url=data.get("addon_url",""),
            author_name=data.get("author_name",""),
            downloads=data.get("downloads",0),
            logo_url=data.get("logo_url"),
            release_filter=data.get("release_filter","all"),
            added_by="dashboard"
        )
        STATS.add_log(f"[UI] Addon {'toegevoegd' if added else 'al in lijst'}: {name}")
        return jsonify({"added": added, "name": name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/watchlist/remove", methods=["POST"])
def api_watchlist_remove():
    data     = request.get_json() or {}
    guild_id = data.get("guild_id", "0")
    addon_id = data.get("addon_id")
    if not addon_id:
        return jsonify({"error": "addon_id vereist"}), 400
    try:
        from bot.services.cache import CacheService
        cache   = CacheService()
        removed = cache.watchlist_remove(guild_id, int(addon_id))
        STATS.add_log(f"[UI] Addon {'verwijderd' if removed else 'niet gevonden'}: ID {addon_id}")
        return jsonify({"removed": removed})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/cf/search", methods=["GET"])
def api_cf_search():
    """Zoek addons op CurseForge — voor de zoekbalk in de UI."""
    query = request.args.get("q","").strip()
    if not query:
        return jsonify({"results": []})
    STATS.add_log(f"[UI] CF zoek: '{query}'")
    return jsonify({"results": [], "query": query,
                    "note": "Start bot voor live zoekresultaten"})

def run_dashboard(host="0.0.0.0", port=5000):
    if not FLASK_OK:
        print("[DASHBOARD] Flask niet geïnstalleerd — dashboard uitgeschakeld")
        return
    import logging
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    print(f"[DASHBOARD] Actief op http://localhost:{port}")
    app.run(host=host, port=port, debug=False, use_reloader=False)

def start_dashboard_thread(port=5000):
    t = threading.Thread(
        target=run_dashboard, kwargs={"port": port}, daemon=True
    )
    t.start()
    return t

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: dashboard.py │ v2.0.0 │ 2026-06-02                         ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
