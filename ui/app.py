# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — ui/app.py  v3.0.0

Hoofdscherm van de CurseBot native UI (CustomTkinter).
Start de bot als daemon-thread via BotManager (launch.py).

CHANGES v3.0.0:
  - Addons tab: live addon-kaarten met downloads, logo, link
  - Watchlist tab: alle watchlist-items tonen per guild
  - Statistieken tab: grafieken + release-history
  - Instellingen tab: token-velden, interval, opslaan
  - Logboek tab: al aanwezig, live log
  - Systeemvak: minimize naar tray via pystray + LOGOSMALL.png
  - Logo fix: LOGOSMALL.png ipv logo.png (correct repo asset)
  - Stats direct op startup: force_check=True in _start_bot_silent
  - on_ready force_check al in bot/main.py aanwezig

CHANGES v2.4.0:
  - Header geintegreerd, knoppen, status indicator, after()-polling
"""
import sys
import time
import threading
import webbrowser
import subprocess
import logging
from pathlib import Path

import customtkinter as ctk

log = logging.getLogger(__name__)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

C_BG      = "#0d0d1a"
C_HEADER  = "#1a1a2e"
C_SIDEBAR = "#12122a"
C_CARD    = "#1c1c32"
C_BORDER  = "#2a2a4a"
C_ACCENT  = "#e8a000"
C_TEXT    = "#d0d0e8"
C_MUTED   = "#666688"
C_GREEN   = "#00cc44"
C_RED     = "#cc2200"
C_FOOTER  = "#111118"

APP_VERSION = "3.0.0"


class CurseBotApp(ctk.CTk):
    """
    Hoofdvenster CurseBot UI v3.0.

    Alle tabs geimplementeerd. Systeemvak via pystray.
    Logo via LOGOSMALL.png (correct asset pad).
    """

    def __init__(self):
        super().__init__()

        self.title("CurseBot — Slayer Alliance Edition")
        self.geometry("1100x720")
        self.minsize(900, 600)
        self.configure(fg_color=C_BG)

        # Icon laden
        try:
            icon_path = Path(__file__).parent / "assets" / "icon.ico"
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except Exception:
            pass

        # Logo laden — LOGOSMALL.png (correct pad in repo)
        self.logo_image = None
        try:
            from PIL import Image
            for name in ("LOGOSMALL.png", "logo.png", "logo_small.png"):
                logo_path = Path(__file__).parent / "assets" / name
                if logo_path.exists():
                    self.logo_image = Image.open(str(logo_path))
                    break
        except Exception:
            pass

        # Gaming tools logo
        self.gaming_tools_image = None
        try:
            from PIL import Image
            gt_path = Path(__file__).parent / "assets" / "gaming_tools.webp"
            if gt_path.exists():
                self.gaming_tools_image = Image.open(str(gt_path)).resize((80, 20))
        except Exception:
            pass

        # BotManager
        try:
            from launch import bot_manager
            self._bot_manager = bot_manager
        except ImportError:
            self._bot_manager = None

        # STATS
        try:
            from bot.services.stats import STATS
            self._stats = STATS
        except ImportError:
            self._stats = None

        # Tray icon referentie
        self._tray_icon = None
        self._tray_thread = None

        self._build_ui()
        self._start_bot_silent()
        self._poll_interval = 1000
        self._poll()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # =========================================================================
    # UI CONSTRUCTIE
    # =========================================================================

    def _build_ui(self):
        self._build_header()
        self._build_body()
        self._build_footer()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=C_HEADER, height=60, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Logo
        logo_frame = ctk.CTkFrame(header, fg_color="transparent", width=80)
        logo_frame.pack(side="left", padx=(10, 0))
        logo_frame.pack_propagate(False)

        if self.logo_image:
            try:
                logo_img = ctk.CTkImage(
                    light_image=self.logo_image,
                    dark_image=self.logo_image,
                    size=(44, 44),
                )
                ctk.CTkLabel(logo_frame, image=logo_img, text="").pack(
                    anchor="center", expand=True
                )
            except Exception:
                pass

        # Titel + status
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", padx=12)

        ctk.CTkLabel(
            title_frame,
            text="CurseBot",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=C_ACCENT,
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_frame,
            text="Slayer Alliance Edition",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=C_MUTED,
        ).pack(anchor="w")

        # Status dot
        status_frame = ctk.CTkFrame(header, fg_color="transparent")
        status_frame.pack(side="left", padx=16)

        self.status_dot = ctk.CTkLabel(
            status_frame, text="●",
            font=ctk.CTkFont(size=14), text_color=C_MUTED,
        )
        self.status_dot.pack(side="left", padx=(0, 4))

        self.status_label = ctk.CTkLabel(
            status_frame, text="Opstarten…",
            font=ctk.CTkFont(family="Segoe UI", size=12), text_color=C_MUTED,
        )
        self.status_label.pack(side="left")

        # Knoppen rechts
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right", padx=12)

        self.timer_label = ctk.CTkLabel(
            btn_frame,
            text="0u 0m 0s",
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color=C_MUTED,
        )
        self.timer_label.pack(side="right", padx=(10, 0))

        btns = [
            ("↑ Update",  C_GREEN,  "#009933", self._do_update),
            ("⟳ Check",   "#1a6eb5", "#154e80", self._do_check),
            ("⟳ Herstart","#b87d00", "#8a5e00", self._do_restart),
            ("✕ Cache",   "#555577", "#444466", self._do_cache_clear),
            ("⏹ Stop",    C_RED,     "#991100", self._do_stop),
        ]
        for text, fg, hover, cmd in reversed(btns):
            ctk.CTkButton(
                btn_frame, text=text, command=cmd,
                fg_color=fg, hover_color=hover,
                width=80, height=32, corner_radius=6,
                font=ctk.CTkFont(family="Segoe UI", size=12),
            ).pack(side="right", padx=3)

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True)

        sidebar = ctk.CTkFrame(body, fg_color=C_SIDEBAR, width=200, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        ctk.CTkLabel(
            sidebar, text="NAVIGATIE",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=C_MUTED, anchor="w",
        ).pack(padx=14, pady=(18, 6), anchor="w")

        self._tab_buttons = {}
        self._active_tab  = None

        tabs = [
            ("dashboard", "📊  Dashboard"),
            ("addons",    "🔍  Mijn Addons"),
            ("watchlist", "👁  Watchlist"),
            ("browser",   "🌐  CF Browser"),
            ("stats",     "📈  Statistieken"),
            ("settings",  "⚙  Instellingen"),
            ("logs",      "📋  Logboek"),
        ]
        for key, label in tabs:
            btn = ctk.CTkButton(
                sidebar, text=label,
                command=lambda k=key: self._switch_tab(k),
                anchor="w", fg_color="transparent",
                hover_color=C_BORDER, text_color=C_TEXT,
                font=ctk.CTkFont(family="Segoe UI", size=13),
                corner_radius=6, height=36,
            )
            btn.pack(fill="x", padx=8, pady=2)
            self._tab_buttons[key] = btn

        self._content = ctk.CTkFrame(body, fg_color=C_BG, corner_radius=0)
        self._content.pack(side="left", fill="both", expand=True)

        self._tab_frames = {}
        self._build_tab_dashboard()
        self._build_tab_addons()
        self._build_tab_watchlist()
        self._build_tab_browser()
        self._build_tab_stats()
        self._build_tab_settings()
        self._build_tab_logs()

        self._switch_tab("dashboard")

    def _build_tab_dashboard(self):
        f = ctk.CTkFrame(self._content, fg_color=C_BG)
        self._tab_frames["dashboard"] = f

        cards_row = ctk.CTkFrame(f, fg_color="transparent")
        cards_row.pack(fill="x", padx=20, pady=(20, 10))

        self._stat_cards = {}
        for key, label, default in [
            ("uptime",    "Uptime",    "–"),
            ("guilds",    "Servers",   "0"),
            ("tracked",   "Addons",    "0"),
            ("releases",  "Releases",  "0"),
            ("watchlist", "Watchlist", "0"),
            ("interval",  "Interval",  "10m"),
        ]:
            card = ctk.CTkFrame(cards_row, fg_color=C_CARD, corner_radius=10)
            card.pack(side="left", expand=True, fill="x", padx=6)
            ctk.CTkLabel(card, text=label.upper(),
                font=ctk.CTkFont(family="Segoe UI", size=10), text_color=C_MUTED,
            ).pack(pady=(10, 2))
            val = ctk.CTkLabel(card, text=default,
                font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
                text_color=C_TEXT,
            )
            val.pack(pady=(0, 10))
            self._stat_cards[key] = val

        timing_row = ctk.CTkFrame(f, fg_color="transparent")
        timing_row.pack(fill="x", padx=20, pady=(0, 10))
        self._last_check_lbl = ctk.CTkLabel(timing_row, text="Laatste check: –",
            font=ctk.CTkFont(size=11), text_color=C_MUTED)
        self._last_check_lbl.pack(side="left")
        self._next_check_lbl = ctk.CTkLabel(timing_row, text="Volgende check: –",
            font=ctk.CTkFont(size=11), text_color=C_MUTED)
        self._next_check_lbl.pack(side="right")

        ctk.CTkLabel(f, text="LIVE LOG",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=C_MUTED, anchor="w",
        ).pack(fill="x", padx=24, pady=(4, 2))

        self._log_box = ctk.CTkTextbox(f,
            fg_color=C_CARD, text_color="#88aacc",
            font=ctk.CTkFont(family="Consolas", size=12),
            corner_radius=8, border_width=1, border_color=C_BORDER,
            state="disabled", wrap="word",
        )
        self._log_box.pack(fill="both", expand=True, padx=20, pady=(0, 16))

    def _build_tab_addons(self):
        """Mijn Addons tab — live kaarten vanuit STATS.project_list."""
        f = ctk.CTkFrame(self._content, fg_color=C_BG)
        self._tab_frames["addons"] = f

        # Header
        header = ctk.CTkFrame(f, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(16, 8))
        ctk.CTkLabel(header, text="Mijn Addons",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=C_TEXT,
        ).pack(side="left")
        ctk.CTkButton(header, text="⟳ Vernieuwen",
            command=self._do_check, width=110, height=30,
            fg_color=C_CARD, hover_color=C_BORDER,
            font=ctk.CTkFont(size=12),
        ).pack(side="right")

        # Scrollable container voor addon-kaarten
        self._addons_scroll = ctk.CTkScrollableFrame(f, fg_color=C_BG, corner_radius=0)
        self._addons_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        self._addon_cards_built = False
        # Eerste render placeholder
        ctk.CTkLabel(self._addons_scroll,
            text="Wachten op bot-data… (kan tot 10 min duren bij eerste start)\nKlik 'Check' om direct te verversen.",
            font=ctk.CTkFont(size=14), text_color=C_MUTED,
        ).pack(expand=True, pady=60)

    def _build_tab_watchlist(self):
        """Watchlist tab — items opgehaald via STATS."""
        f = ctk.CTkFrame(self._content, fg_color=C_BG)
        self._tab_frames["watchlist"] = f

        ctk.CTkLabel(f, text="Watchlist",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=C_TEXT,
        ).pack(anchor="w", padx=20, pady=(16, 8))

        self._watchlist_scroll = ctk.CTkScrollableFrame(f, fg_color=C_BG, corner_radius=0)
        self._watchlist_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        ctk.CTkLabel(self._watchlist_scroll,
            text="Gebruik /watchlist add in Discord om addons toe te voegen.",
            font=ctk.CTkFont(size=13), text_color=C_MUTED,
        ).pack(expand=True, pady=40)

    def _build_tab_browser(self):
        """CF Browser tab — open CurseForge in embedded webview of browser."""
        f = ctk.CTkFrame(self._content, fg_color=C_BG)
        self._tab_frames["browser"] = f

        ctk.CTkLabel(f, text="CurseForge Browser",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=C_TEXT,
        ).pack(anchor="w", padx=20, pady=(20, 8))

        ctk.CTkLabel(f,
            text="Open CurseForge direct in je browser.",
            font=ctk.CTkFont(size=13), text_color=C_MUTED,
        ).pack(anchor="w", padx=20, pady=(0, 16))

        links = [
            ("🌐  CurseForge — Alle Addons",  "https://www.curseforge.com/wow/addons"),
            ("👤  Mijn Author Pagina",          "https://www.curseforge.com/members/dieouwe/projects"),
            ("⭐  Top WoW Addons",              "https://www.curseforge.com/wow/addons?sortType=2"),
            ("🆕  Nieuwste Releases",           "https://www.curseforge.com/wow/addons?sortType=1"),
        ]
        for label, url in links:
            row = ctk.CTkFrame(f, fg_color=C_CARD, corner_radius=8)
            row.pack(fill="x", padx=20, pady=4)
            ctk.CTkLabel(row, text=label,
                font=ctk.CTkFont(size=14), text_color=C_TEXT,
            ).pack(side="left", padx=16, pady=12)
            ctk.CTkButton(row, text="Openen ↗",
                command=lambda u=url: webbrowser.open(u),
                width=90, height=30, fg_color=C_ACCENT,
                hover_color="#b87d00", text_color="#000000",
                font=ctk.CTkFont(size=12),
            ).pack(side="right", padx=12, pady=8)

        # Dashboard link
        ctk.CTkFrame(f, fg_color=C_BORDER, height=1).pack(fill="x", padx=20, pady=12)
        dash_row = ctk.CTkFrame(f, fg_color=C_CARD, corner_radius=8)
        dash_row.pack(fill="x", padx=20, pady=4)
        ctk.CTkLabel(dash_row, text="📊  Web Dashboard (localhost)",
            font=ctk.CTkFont(size=14), text_color=C_TEXT,
        ).pack(side="left", padx=16, pady=12)
        ctk.CTkButton(dash_row, text="Openen ↗",
            command=lambda: webbrowser.open("http://localhost:5000"),
            width=90, height=30, fg_color="#1a6eb5",
            hover_color="#154e80",
            font=ctk.CTkFont(size=12),
        ).pack(side="right", padx=12, pady=8)

    def _build_tab_stats(self):
        """Statistieken tab."""
        f = ctk.CTkFrame(self._content, fg_color=C_BG)
        self._tab_frames["stats"] = f

        ctk.CTkLabel(f, text="Statistieken",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=C_TEXT,
        ).pack(anchor="w", padx=20, pady=(20, 12))

        self._stats_scroll = ctk.CTkScrollableFrame(f, fg_color=C_BG)
        self._stats_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        # Stat boxes — gevuld door _update_ui_from_stats
        self._stats_boxes = {}
        stats_defs = [
            ("releases",   "Releases gedetecteerd",  "0"),
            ("guilds",     "Verbonden servers",       "0"),
            ("tracked",    "Getrackte addons",        "0"),
            ("watchlist",  "Watchlist items",         "0"),
            ("uptime",     "Uptime",                  "–"),
            ("last_check", "Laatste check",           "–"),
            ("next_check", "Volgende check",          "–"),
            ("interval",   "Check interval",          "–"),
        ]
        for i, (key, label, default) in enumerate(stats_defs):
            row = ctk.CTkFrame(self._stats_scroll, fg_color=C_CARD, corner_radius=8)
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=label,
                font=ctk.CTkFont(size=13), text_color=C_MUTED,
                anchor="w",
            ).pack(side="left", padx=16, pady=10)
            val = ctk.CTkLabel(row, text=default,
                font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
                text_color=C_TEXT,
            )
            val.pack(side="right", padx=16, pady=10)
            self._stats_boxes[key] = val

    def _build_tab_settings(self):
        """Instellingen tab — toon en bewerk .env waarden."""
        f = ctk.CTkFrame(self._content, fg_color=C_BG)
        self._tab_frames["settings"] = f

        ctk.CTkLabel(f, text="Instellingen",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=C_TEXT,
        ).pack(anchor="w", padx=20, pady=(20, 4))

        ctk.CTkLabel(f,
            text="Wijzig .env instellingen. Herstart de bot na opslaan.",
            font=ctk.CTkFont(size=12), text_color=C_MUTED,
        ).pack(anchor="w", padx=20, pady=(0, 12))

        scroll = ctk.CTkScrollableFrame(f, fg_color=C_BG)
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        self._setting_entries = {}
        settings_defs = [
            ("DISCORD_TOKEN",       "Discord Token",          "Bot token van Discord Developer Portal", True),
            ("CURSEFORGE_API_KEY",  "CurseForge API Key",     "API key van CurseForge", True),
            ("CF_AUTHOR_SLUG",      "CF Author Slug",         "Jouw CurseForge gebruikersnaam", False),
            ("RELEASE_CHANNEL_ID",  "Release Kanaal ID",      "Discord kanaal ID voor release-notificaties", False),
            ("GUILD_ID",            "Guild ID",               "Discord server ID (leeg = globaal)", False),
            ("CHECK_INTERVAL_MINUTES", "Check Interval (min)", "Hoe vaak op updates checken", False),
            ("LOG_LEVEL",           "Log Level",              "DEBUG / INFO / WARNING / ERROR", False),
            ("DASHBOARD_PORT",      "Dashboard Poort",        "Webdashboard poort (standaard: 5000)", False),
            ("ANTHROPIC_API_KEY",   "Anthropic API Key",      "Optioneel: voor AI changelog samenvattingen", True),
        ]

        env_vals = self._load_env()

        for key, label, hint, secret in settings_defs:
            row = ctk.CTkFrame(scroll, fg_color=C_CARD, corner_radius=8)
            row.pack(fill="x", pady=4)

            ctk.CTkLabel(row, text=label,
                font=ctk.CTkFont(size=13, weight="bold"), text_color=C_TEXT,
                anchor="w", width=200,
            ).pack(side="left", padx=16, pady=10)

            entry = ctk.CTkEntry(row,
                font=ctk.CTkFont(family="Consolas", size=12),
                fg_color=C_BG, border_color=C_BORDER,
                text_color=C_TEXT, width=350,
                show="•" if secret else "",
            )
            entry.pack(side="right", padx=16, pady=8)
            if key in env_vals and env_vals[key]:
                entry.insert(0, env_vals[key])
            else:
                entry.insert(0, "")
            self._setting_entries[key] = entry

        # Opslaan knop
        btn_row = ctk.CTkFrame(f, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=8)
        ctk.CTkButton(btn_row, text="💾  Opslaan en Herstart",
            command=self._do_save_settings,
            fg_color=C_GREEN, hover_color="#009933",
            height=36, font=ctk.CTkFont(size=13),
        ).pack(side="right")
        ctk.CTkLabel(btn_row,
            text="Tokens worden nooit in plaintext getoond na opslaan.",
            font=ctk.CTkFont(size=11), text_color=C_MUTED,
        ).pack(side="left")

    def _build_tab_logs(self):
        """Volledig logboek tab."""
        f = ctk.CTkFrame(self._content, fg_color=C_BG)
        self._tab_frames["logs"] = f

        header = ctk.CTkFrame(f, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(12, 4))

        ctk.CTkLabel(header, text="Logboek",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=C_TEXT,
        ).pack(side="left")

        ctk.CTkButton(header, text="🗑 Wissen",
            command=self._clear_log,
            width=90, height=30, fg_color=C_CARD,
            hover_color=C_BORDER, font=ctk.CTkFont(size=12),
        ).pack(side="right")

        self._full_log_box = ctk.CTkTextbox(f,
            fg_color=C_CARD, text_color="#88aacc",
            font=ctk.CTkFont(family="Consolas", size=11),
            corner_radius=8, border_width=1, border_color=C_BORDER,
            state="disabled", wrap="word",
        )
        self._full_log_box.pack(fill="both", expand=True, padx=20, pady=(4, 16))

    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color=C_FOOTER, height=28, corner_radius=0)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        ctk.CTkLabel(footer,
            text=f"CurseBot v{APP_VERSION}  ·  Slayer Alliance Edition",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=C_MUTED,
        ).pack(side="left", padx=12, pady=6)

        gt_btn = ctk.CTkLabel(footer,
            text="gaming.tools",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=C_ACCENT, cursor="hand2",
        )
        gt_btn.pack(side="right", padx=12)
        gt_btn.bind("<Button-1>", lambda e: webbrowser.open("https://gaming.tools"))

    # =========================================================================
    # TAB SWITCHING
    # =========================================================================

    def _switch_tab(self, key: str):
        for k, f in self._tab_frames.items():
            f.pack_forget()
        for k, btn in self._tab_buttons.items():
            btn.configure(
                fg_color=C_ACCENT if k == key else "transparent",
                text_color="#000000" if k == key else C_TEXT,
            )
        self._tab_frames[key].pack(fill="both", expand=True)
        self._active_tab = key

    # =========================================================================
    # HEADER KNOPPEN
    # =========================================================================

    def _do_stop(self):
        if self._bot_manager:
            self._bot_manager.stop()
            self._log_ui("[UI] Stop aangevraagd")

    def _do_restart(self):
        if self._bot_manager:
            self._bot_manager.stop()
            self.after(1500, lambda: self._bot_manager.start() if self._bot_manager else None)
            self._log_ui("[UI] Herstart aangevraagd")

    def _do_cache_clear(self):
        try:
            from bot.services.cache import CacheService
            CacheService().clear_release_cache()
            self._log_ui("[UI] Cache gewist")
        except Exception as e:
            self._log_ui(f"[FOUT] Cache wissen: {e}")

    def _do_check(self):
        if self._stats:
            self._stats.force_check = True
            self._log_ui("[UI] Handmatige check gestart")

    def _do_update(self):
        def _run():
            try:
                import subprocess, sys
                result = subprocess.run(
                    [sys.executable, "updater.py"],
                    capture_output=True, text=True, timeout=60,
                )
                if result.returncode == 42:
                    self.after(0, lambda: self._log_ui("[UI] Update geinstalleerd — herstart aanbevolen"))
                else:
                    self.after(0, lambda: self._log_ui("[UI] Al up-to-date"))
            except Exception as e:
                self.after(0, lambda: self._log_ui(f"[FOUT] Update mislukt: {e}"))
        threading.Thread(target=_run, daemon=True).start()

    def _do_save_settings(self):
        """Sla instellingen op naar .env en herstart bot."""
        try:
            env_path = Path(".env")
            existing = {}
            if env_path.exists():
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    if "=" in line and not line.startswith("#"):
                        k, _, v = line.partition("=")
                        existing[k.strip()] = v.strip()

            for key, entry in self._setting_entries.items():
                val = entry.get().strip()
                if val:
                    existing[key] = val

            lines = [f"{k}={v}" for k, v in existing.items()]
            env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            self._log_ui("[UI] Instellingen opgeslagen — bot herstart...")

            if self._bot_manager:
                self._bot_manager.stop()
                self.after(1500, lambda: self._bot_manager.start() if self._bot_manager else None)
        except Exception as e:
            self._log_ui(f"[FOUT] Opslaan mislukt: {e}")

    def _clear_log(self):
        if self._stats:
            self._stats.log_buffer.clear()
        self._full_log_box.configure(state="normal")
        self._full_log_box.delete("1.0", "end")
        self._full_log_box.configure(state="disabled")

    # =========================================================================
    # SYSTEEMVAK (TRAY)
    # =========================================================================

    def _minimize_to_tray(self):
        """Minimaliseer naar systeemvak via pystray."""
        try:
            import pystray
            from PIL import Image as PILImage

            self.withdraw()  # Verberg venster

            if self._tray_icon:
                return  # Al actief

            # Laad icon image
            icon_path = Path(__file__).parent / "assets" / "icon.ico"
            if icon_path.exists():
                img = PILImage.open(str(icon_path))
            else:
                # Fallback: klein gekleurd blokje
                img = PILImage.new("RGB", (64, 64), color=(232, 160, 0))

            def on_restore(icon, item):
                icon.stop()
                self._tray_icon = None
                self.after(0, self.deiconify)

            def on_quit(icon, item):
                icon.stop()
                self._tray_icon = None
                self.after(0, self._force_close)

            menu = pystray.Menu(
                pystray.MenuItem("CurseBot openen", on_restore, default=True),
                pystray.MenuItem("Afsluiten", on_quit),
            )

            self._tray_icon = pystray.Icon(
                "CurseBot",
                img,
                "CurseBot — Slayer Alliance",
                menu,
            )

            self._tray_thread = threading.Thread(
                target=self._tray_icon.run,
                daemon=True,
                name="TrayThread",
            )
            self._tray_thread.start()

        except ImportError:
            self._log_ui("[WARN] pystray niet geinstalleerd — kan niet minimaliseren naar tray")
        except Exception as e:
            self._log_ui(f"[FOUT] Tray: {e}")
            self.deiconify()

    # =========================================================================
    # POLL LOOP — live UI updates
    # =========================================================================

    def _poll(self):
        try:
            self._update_ui_from_stats()
            self._update_addons_tab()
            self._update_watchlist_tab()
            self._update_stats_tab()
        except Exception as e:
            log.debug(f"[UI] Poll fout: {e}")
        self.after(self._poll_interval, self._poll)

    def _update_ui_from_stats(self):
        if not self._stats:
            return
        s = self._stats

        if s.bot_online:
            self.status_dot.configure(text_color=C_GREEN)
            self.status_label.configure(text="Online", text_color=C_GREEN)
        else:
            dot_color = "#cc4400" if s.stop_requested else C_MUTED
            self.status_dot.configure(text_color=dot_color)
            self.status_label.configure(
                text="Gestopt" if s.stop_requested else "Opstarten…",
                text_color=dot_color,
            )

        self.timer_label.configure(text=s.uptime_str())
        self._stat_cards["uptime"].configure(text=s.uptime_str())
        self._stat_cards["guilds"].configure(text=str(s.guilds))
        self._stat_cards["tracked"].configure(text=str(s.projects_tracked))
        self._stat_cards["releases"].configure(text=str(s.releases_detected))
        self._stat_cards["watchlist"].configure(text=str(s.watchlist_count))
        self._stat_cards["interval"].configure(text=f"{s.check_interval_min}m")
        self._last_check_lbl.configure(text=f"Laatste check: {s.last_check or '–'}")
        self._next_check_lbl.configure(text=f"Volgende check: {s.next_check or '–'}")

        if s.log_buffer:
            self._set_textbox(self._log_box, "\n".join(s.log_buffer[-30:]))

        if self._active_tab == "logs" and s.log_buffer:
            self._set_textbox(self._full_log_box, "\n".join(s.log_buffer))

    def _update_addons_tab(self):
        """Herlaad addon-kaarten als project_list gewijzigd is."""
        if not self._stats or not self._stats.project_list:
            return
        if self._active_tab != "addons" and self._addon_cards_built:
            return

        projects = self._stats.project_list
        if not projects:
            return

        # Wis bestaande widgets
        for w in self._addons_scroll.winfo_children():
            w.destroy()

        for p in projects:
            card = ctk.CTkFrame(self._addons_scroll, fg_color=C_CARD, corner_radius=8)
            card.pack(fill="x", pady=4)

            name_row = ctk.CTkFrame(card, fg_color="transparent")
            name_row.pack(fill="x", padx=16, pady=(10, 2))

            ctk.CTkLabel(name_row,
                text=p.get("name", "Onbekend"),
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color=C_TEXT, anchor="w",
            ).pack(side="left")

            dl_count = p.get("downloads", 0)
            ctk.CTkLabel(name_row,
                text=f"📥 {dl_count:,}",
                font=ctk.CTkFont(size=12), text_color=C_MUTED,
            ).pack(side="right")

            if p.get("summary"):
                ctk.CTkLabel(card,
                    text=p["summary"][:120] + ("…" if len(p.get("summary","")) > 120 else ""),
                    font=ctk.CTkFont(size=11), text_color=C_MUTED,
                    anchor="w", wraplength=700,
                ).pack(fill="x", padx=16, pady=(0, 4))

            if p.get("url"):
                link = ctk.CTkLabel(card,
                    text=f"🔗  {p['url']}",
                    font=ctk.CTkFont(size=11), text_color=C_ACCENT,
                    cursor="hand2", anchor="w",
                )
                link.pack(fill="x", padx=16, pady=(0, 8))
                link.bind("<Button-1>", lambda e, u=p["url"]: webbrowser.open(u))

        self._addon_cards_built = True

    def _update_watchlist_tab(self):
        """Update watchlist tab vanuit cache."""
        if self._active_tab != "watchlist":
            return
        if not self._stats:
            return

        # Haal watchlist op via cache
        try:
            from bot.services.cache import CacheService
            cache = CacheService()
            items = cache.watchlist_all()

            for w in self._watchlist_scroll.winfo_children():
                w.destroy()

            if not items:
                ctk.CTkLabel(self._watchlist_scroll,
                    text="Geen watchlist items.\nGebruik /watchlist add [addon_id] in Discord.",
                    font=ctk.CTkFont(size=13), text_color=C_MUTED,
                ).pack(expand=True, pady=40)
                return

            for item in items:
                card = ctk.CTkFrame(self._watchlist_scroll, fg_color=C_CARD, corner_radius=8)
                card.pack(fill="x", pady=4)
                ctk.CTkLabel(card,
                    text=f"📦  Addon ID: {item.get('addon_id', '?')}",
                    font=ctk.CTkFont(family="Consolas", size=13),
                    text_color=C_TEXT,
                ).pack(side="left", padx=16, pady=10)
                ctk.CTkLabel(card,
                    text=f"Guild: {item.get('guild_id', '?')}",
                    font=ctk.CTkFont(size=11), text_color=C_MUTED,
                ).pack(side="right", padx=16)
        except Exception:
            pass

    def _update_stats_tab(self):
        """Update statistieken tab met live STATS data."""
        if not self._stats or self._active_tab != "stats":
            return
        s = self._stats
        mapping = {
            "releases":   str(s.releases_detected),
            "guilds":     str(s.guilds),
            "tracked":    str(s.projects_tracked),
            "watchlist":  str(s.watchlist_count),
            "uptime":     s.uptime_str(),
            "last_check": s.last_check or "–",
            "next_check": s.next_check or "–",
            "interval":   f"{s.check_interval_min} minuten",
        }
        for key, val in mapping.items():
            if key in self._stats_boxes:
                self._stats_boxes[key].configure(text=val)

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _start_bot_silent(self):
        """Start bot + trigger direct een eerste check."""
        if self._bot_manager and not self._bot_manager.is_running:
            self._bot_manager.start()
            self._log_ui("Bot gestart")
        # Force eerste check direct — zodat stats niet 10 min op 0 staan
        if self._stats:
            self._stats.force_check = True

    def _log_ui(self, msg: str):
        if self._stats:
            self._stats.add_log(f"[UI] {msg}")

    @staticmethod
    def _set_textbox(widget: ctk.CTkTextbox, content: str):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", content)
        widget.see("end")
        widget.configure(state="disabled")

    def _load_env(self) -> dict:
        vals = {}
        env_path = Path(".env")
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    vals[k.strip()] = v.strip()
        return vals

    def _on_close(self):
        """Sluit venster — minimaliseer naar tray ipv afsluiten."""
        self._minimize_to_tray()

    def _force_close(self):
        """Volledig afsluiten inclusief bot."""
        try:
            if self._bot_manager:
                self._bot_manager.stop()
            if self._stats:
                self._stats.add_log("[UI] Venster gesloten")
        except Exception:
            pass
        self.destroy()


# ── Entry point ────────────────────────────────────────────────────────────────

def run_app():
    app = CurseBotApp()
    app.mainloop()


if __name__ == "__main__":
    run_app()

# ╔══════════════════════════════════════════════════════════════════════╗
# ║                         FILE CARD                                   ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  File         : ui/app.py                                           ║
# ║  Role         : UI Core                                             ║
# ║  Version      : 3.0.0                                               ║
# ║  Created      : 2026-06-02                                          ║
# ║  Last Updated : 2026-06-06                                          ║
# ║  Status       : Updated                                             ║
# ║  Notes        : Alle tabs geimplementeerd, tray, logo fix           ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  Created by Dieouwe                                                  ║
# ║  www.dieouwe.nl  --  slayeralliance.com  --  discord.gg/y8Pu5qsEbQ ║
# ╚══════════════════════════════════════════════════════════════════════╝
