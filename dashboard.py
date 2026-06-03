# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""CurseBot — dashboard.py v2.1.0 — Flask API backend voor het web dashboard.

FIXES v2.1.0:
  - BUGFIX: p.id → p["id"] in api_stats (project_list zijn dicts, geen objecten)
  - FEATURE: /api/stop endpoint — zet STATS.stop_requested flag
  - FEATURE: /api/cf/addon/<id> endpoint toegevoegd
  - FEATURE: GUILD_ID toegevoegd aan ALLOWED_SETTINGS
"""
import sys
import json
import threading
import subprocess
from pathlib import Path

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
    # project_list zijn dicts — gebruik dict-toegang (["key"]), NIET object-attributen (.key)
    pl = getattr(STATS, "project_list", [])
    data["projects"] = [
        {
            "id":       p.get("id",       0),
            "name":     p.get("name",     ""),
            "slug":     p.get("slug",     ""),
            "url":      p.get("url",      ""),
            "downloads":p.get("downloads",0),
            "logo_url": p.get("logo_url", None),
            "summary":  p.get("summary",  ""),
            "author_name": p.get("author_name", ""),
        }
        for p in pl
        if isinstance(p, dict)   # veiligheidscheck: negeer niet-dict items
    ]
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
    try:
        STATS.force_check = True
        STATS.add_log("[DASHBOARD] Handmatige check getriggerd")
        return jsonify({"ok": True, "message": "Check getriggerd"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stop", methods=["POST"])
def api_stop():
    """Zet stop_requested flag — bot main loop pikt dit op en stopt netjes."""
    try:
        STATS.stop_requested = True
        STATS.bot_online     = False
        STATS.add_log("[DASHBOARD] Stop aangevraagd via UI")
        return jsonify({"ok": True, "message": "Bot stopt..."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Settings API ───────────────────────────────────────────────────────────────
ALLOWED_SETTINGS = {
    "CF_AUTHOR_SLUG", "CF_AUTHOR_ID", "GUILD_ID",
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

# ── Watchlist API ──────────────────────────────────────────────────────────────
@app.route("/api/watchlist", methods=["GET"])
def api_watchlist_get():
    try:
        from bot.services.cache import CacheService
        cache    = CacheService()
        guild_id = request.args.get("guild_id", "0")
        items    = cache.watchlist_get(guild_id) if guild_id != "0" else cache.watchlist_all()
        return jsonify({"items": items, "count": len(items)})
    except Exception as e:
        return jsonify({"items": [], "count": 0, "error": str(e)})

@app.route("/api/watchlist/add", methods=["POST"])
def api_watchlist_add():
    try:
        from bot.services.cache import CacheService
        data     = request.get_json() or {}
        addon_id = data.get("addon_id")
        guild_id = data.get("guild_id", "0")
        if not addon_id:
            return jsonify({"error": "addon_id vereist"}), 400
        cache = CacheService()
        added = cache.watchlist_add(
            guild_id=guild_id,
            addon_id=int(addon_id),
            addon_name=data.get("addon_name", ""),
            addon_slug=data.get("addon_slug", ""),
            addon_url=data.get("addon_url", ""),
            author_name=data.get("author_name", ""),
            downloads=data.get("downloads", 0),
            logo_url=data.get("logo_url"),
            release_filter=data.get("release_filter", "all"),
            added_by="dashboard",
        )
        STATS.add_log(f"[UI] Addon {'toegevoegd' if added else 'al aanwezig'}: {data.get('addon_name','?')}")
        return jsonify({"added": added})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/watchlist/remove", methods=["POST"])
def api_watchlist_remove():
    try:
        from bot.services.cache import CacheService
        data     = request.get_json() or {}
        addon_id = data.get("addon_id")
        guild_id = data.get("guild_id", "0")
        if not addon_id:
            return jsonify({"error": "addon_id vereist"}), 400
        cache   = CacheService()
        removed = cache.watchlist_remove(guild_id, int(addon_id))
        STATS.add_log(f"[UI] Addon {'verwijderd' if removed else 'niet gevonden'}: ID {addon_id}")
        return jsonify({"removed": removed})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── CF Search API (voor UI zoekfunctie) ───────────────────────────────────────
@app.route("/api/cf/search", methods=["GET"])
def api_cf_search():
    """Doorsturen naar CurseForge via de bot's CF service — vereist draaiende bot."""
    try:
        query = request.args.get("q", "").strip()
        if not query:
            return jsonify({"results": [], "error": "geen query"}), 400
        # Haal resultaten op uit project_list als fallback
        pl = getattr(STATS, "project_list", [])
        hits = [p for p in pl if query.lower() in p.get("name", "").lower()]
        return jsonify({"results": hits})
    except Exception as e:
        return jsonify({"results": [], "error": str(e)}), 500

@app.route("/api/cf/addon/<int:addon_id>", methods=["GET"])
def api_cf_addon(addon_id: int):
    """Haal addon info op uit lokale cache."""
    try:
        from bot.services.cache import CacheService
        meta = CacheService().addon_meta_get(addon_id)
        if meta:
            return jsonify(meta)
        return jsonify({"error": "niet gevonden"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Server start ───────────────────────────────────────────────────────────────
def start_dashboard_thread(port: int = 5000):
    if not FLASK_OK or not app:
        print("[DASHBOARD] Flask niet beschikbaar — dashboard overgeslagen")
        return
    import logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)
    t = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False),
        daemon=True, name="DashboardThread"
    )
    t.start()
    print(f"[DASHBOARD] Actief op http://localhost:{port}")

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: dashboard.py │ v2.1.0 │ 2026-06-03                         ║
# ║  Fix: p["id"] ipv p.id (project_list zijn dicts)                  ║
# ║  Add: /api/stop endpoint, GUILD_ID in ALLOWED_SETTINGS             ║
# ║  Add: /api/cf/addon/<id> endpoint                                  ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
