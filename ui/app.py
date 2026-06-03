# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — ui/app.py  v1.0.0
Native desktop UI via CustomTkinter.
Start via: python -m ui.app  (of automatisch vanuit start_cursebot.bat)

Layout:
  ┌─────────────────────────────────────────────────────────────────────┐
  │  HEADER  — logo · status · uptime · actieknoppen                   │
  ├──────────────┬──────────────────────────────────────────────────────┤
  │              │  GRID (unieke widget IDs)                            │
  │   SIDEBAR    │  ┌─stat1─┬─stat2─┬─stat3─┬─stat4─┐                 │
  │   navigatie  │  └───────┴───────┴───────┴───────┘                 │
  │   + links    │  ┌─zoekbalk──────────────────────┐                 │
  │              │  ├─watchlist──────────────────────┤                 │
  │              │  └─log─────────────────────────────┘                │
  ├──────────────┴──────────────────────────────────────────────────────┤
  │  FOOTER — versie · links · commit sha                               │
  └─────────────────────────────────────────────────────────────────────┘
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import asyncio
import urllib.request
import urllib.parse
import json
import sys
import os
import subprocess
import webbrowser
from pathlib import Path
from datetime import datetime

# ── Configuratie ───────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

BASE_DIR  = Path(__file__).parent.parent
API_BASE  = "http://localhost:5000"

# Kleurenpalet — Slayer Alliance
C_BG       = "#0b0d12"
C_BG2      = "#10131a"
C_BG3      = "#161922"
C_BORDER   = "#1e2235"
C_GOLD     = "#f5a623"
C_BLUE     = "#3d9eff"
C_GREEN    = "#2ecc71"
C_RED      = "#e74c3c"
C_PURPLE   = "#a78bfa"
C_TEXT     = "#cdd6f4"
C_MUTED    = "#6c7086"
C_DISCORD  = "#5865f2"

FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_BODY  = ("Segoe UI", 15)
FONT_SMALL = ("Segoe UI", 13)
FONT_MONO  = ("Consolas", 13)
FONT_MONO_SM = ("Consolas", 12)


# ── API helper ─────────────────────────────────────────────────────────────────
def api_get(endpoint: str, timeout: int = 5) -> dict | None:
    try:
        url = f"{API_BASE}{endpoint}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None


def api_post(endpoint: str, data: dict, timeout: int = 10) -> dict | None:
    try:
        url     = f"{API_BASE}{endpoint}"
        payload = json.dumps(data).encode()
        req     = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None


def cf_search_web(query: str) -> list[dict]:
    """Zoek addons via CF website — werkt zonder bot."""
    try:
        params = urllib.parse.urlencode({
            "page": 1, "pageSize": 8,
            "sortBy": "relevancy", "search": query
        })
        url = f"https://www.curseforge.com/api/v1/mods/search?gameId=1&{params}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "CurseBot-UI/2.0",
            "Accept": "application/json"
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            data   = json.loads(r.read())
            return data.get("data", [])
    except Exception:
        return []


# ── Hoofd applicatie ───────────────────────────────────────────────────────────
def _load_image_async(widget_ref, url: str, size: tuple = (48, 48),
                      placeholder_text: str = "⚡", app_ref=None):
    """
    Laad een afbeelding asynchroon in een daemon thread.
    Zodra geladen → update het widget via app.after().
    widget_ref: lijst met [frame_widget] zodat we kunnen checken of nog geldig
    """
    def task():
        try:
            import urllib.request as _ur
            from PIL import Image, ImageTk
            import io
            with _ur.urlopen(url, timeout=6) as r:
                data = r.read()
            img   = Image.open(io.BytesIO(data)).convert("RGBA").resize(
                size, Image.LANCZOS
            )
            photo = ImageTk.PhotoImage(img)

            def update():
                try:
                    frame = widget_ref[0]
                    if not frame.winfo_exists():
                        return
                    # Verwijder placeholder
                    for child in frame.winfo_children():
                        child.destroy()
                    import tkinter as _tk
                    lbl = _tk.Label(
                        frame, image=photo,
                        bg="#10131a", bd=0, relief="flat"
                    )
                    lbl.image = photo   # GC guard
                    lbl.pack(expand=True)
                except Exception:
                    pass

            if app_ref:
                app_ref.after(0, update)
        except Exception:
            pass   # Timeout of load fout — placeholder blijft

    import threading
    t = threading.Thread(target=task, daemon=True, name="ImgLoader")
    t.start()


class CurseBotApp(ctk.CTk):
    def __init__(self, bot_manager=None):
        super().__init__()

        # BotManager — optioneel (None als UI standalone draait)
        self._bot_manager = bot_manager

        # Window setup
        self.title("CurseBot — Slayer Alliance Edition")
        self.geometry("1200x740")
        self.minsize(1000, 660)
        self.configure(fg_color=C_BG)

        # State
        self._bot_online   = False
        self._stats        = {}
        self._watchlist    = []
        self._search_results = []
        self._active_tab   = "dashboard"
        self._poll_active  = True
        self._guild_id     = "0"

        # Icon
        try:
            icon_path = BASE_DIR / "ui" / "assets" / "icon.ico"
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except Exception:
            pass

        # Protocol
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Build UI
        self._build_header()
        self._build_body()
        self._build_footer()

        # Start poll
        self._start_poll()
        self.after(500, self._refresh)

        # Tray icon referentie
        self._tray_icon = None

        # Bind minimize event → naar tray
        self.bind("<Unmap>", self._on_unmap)

        # Setup wizard — toon als verplichte keys ontbreken
        self.after(300, self._check_setup)

    # ── HEADER (wid: hdr_*) ───────────────────────────────────────────────────
    def _build_header(self):
        self.hdr_frame = ctk.CTkFrame(
            self, fg_color=C_BG3, corner_radius=0, height=56,
            border_width=1, border_color=C_BORDER
        )
        self.hdr_frame.pack(fill="x", side="top")
        self.hdr_frame.pack_propagate(False)

        # Logo afbeelding — LOGOSMALL.png met transparantie fix
        try:
            from PIL import Image
            _logo_path = BASE_DIR / "ui" / "assets" / "LOGOSMALL.png"
            if _logo_path.exists():
                _img = Image.open(_logo_path).convert("RGBA")
                # Maak zwarte/donkere pixels transparant (achtergrond fix)
                datas = _img.getdata()
                new_data = []
                for r, g, b, a in datas:
                    # Pixels donkerder dan drempel → volledig transparant
                    if r < 30 and g < 30 and b < 30:
                        new_data.append((r, g, b, 0))
                    else:
                        new_data.append((r, g, b, a))
                _img.putdata(new_data)
                _logo_pil = _img.resize((38, 38), Image.LANCZOS)
                self._hdr_logo_img = ctk.CTkImage(
                    light_image=_logo_pil, dark_image=_logo_pil,
                    size=(38, 38)
                )
                ctk.CTkLabel(
                    self.hdr_frame,
                    image=self._hdr_logo_img,
                    text="",
                    fg_color="transparent",
                    bg_color="transparent"
                ).pack(side="left", padx=(10, 6), pady=8)
        except Exception:
            pass  # Fallback: geen logo — tekst blijft zichtbaar

        # Tekst logo
        self.hdr_logo_lbl = ctk.CTkLabel(
            self.hdr_frame, text="CurseBot",
            font=("Segoe UI", 16, "bold"), text_color=C_GOLD
        )
        self.hdr_logo_lbl.pack(side="left", padx=(0, 4), pady=12)

        self.hdr_edition_lbl = ctk.CTkLabel(
            self.hdr_frame, text="Slayer Alliance Edition",
            font=FONT_SMALL, text_color=C_MUTED
        )
        self.hdr_edition_lbl.pack(side="left", padx=(0, 20), pady=12)

        # Status indicator
        self.hdr_status_dot = ctk.CTkLabel(
            self.hdr_frame, text="●",
            font=("Segoe UI", 14), text_color=C_RED, width=20
        )
        self.hdr_status_dot.pack(side="left", padx=(0, 2))

        self.hdr_status_lbl = ctk.CTkLabel(
            self.hdr_frame, text="Verbinden...",
            font=FONT_SMALL, text_color=C_MUTED
        )
        self.hdr_status_lbl.pack(side="left", padx=(0, 16))

        # Rechts: uptime + knoppen
        self.hdr_uptime_lbl = ctk.CTkLabel(
            self.hdr_frame, text="",
            font=FONT_MONO_SM, text_color=C_MUTED
        )
        self.hdr_uptime_lbl.pack(side="right", padx=(0, 12))

        self.hdr_update_btn = ctk.CTkButton(
            self.hdr_frame, text="↑ Update",
            font=FONT_SMALL, width=80, height=28,
            fg_color=C_BG2, hover_color=C_BG3,
            border_color=C_GOLD, border_width=1,
            text_color=C_GOLD,
            command=self._do_update
        )
        self.hdr_update_btn.pack(side="right", padx=(0, 6), pady=10)

        self.hdr_check_btn = ctk.CTkButton(
            self.hdr_frame, text="↺ Check",
            font=FONT_SMALL, width=74, height=28,
            fg_color=C_BG2, hover_color=C_BG3,
            border_color=C_BLUE, border_width=1,
            text_color=C_BLUE,
            command=self._do_check
        )
        self.hdr_check_btn.pack(side="right", padx=(0, 6), pady=10)

        self.hdr_stop_btn = ctk.CTkButton(
            self.hdr_frame, text="⏹ Stop",
            font=FONT_SMALL, width=66, height=28,
            fg_color=C_BG2, hover_color=C_BG3,
            border_color=C_RED, border_width=1,
            text_color=C_RED,
            command=self._do_stop
        )
        self.hdr_stop_btn.pack(side="right", padx=(0, 6), pady=10)

        # Start knop — zichtbaar als bot offline is
        self.hdr_start_btn = ctk.CTkButton(
            self.hdr_frame, text="▶ Start",
            font=FONT_SMALL, width=66, height=28,
            fg_color=C_BG2, hover_color=C_BG3,
            border_color=C_GREEN, border_width=1,
            text_color=C_GREEN,
            command=self._do_start
        )
        self.hdr_start_btn.pack(side="right", padx=(0, 6), pady=10)
        self.hdr_start_btn.pack_forget()  # verborgen bij start (bot draait)

        self.hdr_reset_btn = ctk.CTkButton(
            self.hdr_frame, text="✕ Cache",
            font=FONT_SMALL, width=72, height=28,
            fg_color=C_BG2, hover_color=C_BG3,
            border_color=C_RED, border_width=1,
            text_color=C_RED,
            command=self._do_reset
        )
        self.hdr_reset_btn.pack(side="right", padx=(0, 8), pady=10)

    # ── BODY ──────────────────────────────────────────────────────────────────
    def _build_body(self):
        self.body_frame = ctk.CTkFrame(self, fg_color=C_BG, corner_radius=0)
        self.body_frame.pack(fill="both", expand=True)
        self.body_frame.grid_columnconfigure(1, weight=1)
        self.body_frame.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()

    # ── SIDEBAR (wid: sb_*) ───────────────────────────────────────────────────
    def _build_sidebar(self):
        self.sb_frame = ctk.CTkFrame(
            self.body_frame, fg_color=C_BG3,
            corner_radius=0, width=200,
            border_width=1, border_color=C_BORDER
        )
        self.sb_frame.grid(row=0, column=0, sticky="nsew")
        self.sb_frame.pack_propagate(False)

        # Nav label
        self.sb_nav_lbl = ctk.CTkLabel(
            self.sb_frame, text="MENU",
            font=("Segoe UI", 9, "bold"), text_color=C_MUTED
        )
        self.sb_nav_lbl.pack(anchor="w", padx=16, pady=(14, 6))

        # Nav buttons
        nav_items = [
            ("dashboard",   "⚡",  "Dashboard"),
            ("addons",      "📦",  "Mijn addons"),
            ("search",      "🔍",  "Zoeken"),
            ("watchlist",   "📋",  "Watchlist"),
            ("stats",       "📊",  "Statistieken"),
            ("settings",    "⚙️",  "Instellingen"),
        ]
        self.sb_nav_btns = {}
        for tab_id, icon, label in nav_items:
            btn = ctk.CTkButton(
                self.sb_frame,
                text=f"  {icon}  {label}",
                font=FONT_BODY, anchor="w",
                fg_color=C_GOLD if tab_id == "dashboard" else "transparent",
                hover_color=C_BG2,
                text_color="#000000" if tab_id == "dashboard" else C_TEXT,
                height=38, corner_radius=6,
                command=lambda t=tab_id: self._switch_tab(t)
            )
            btn.pack(fill="x", padx=8, pady=2)
            self.sb_nav_btns[tab_id] = btn

        # Separator
        ctk.CTkFrame(
            self.sb_frame, fg_color=C_BORDER, height=1, corner_radius=0
        ).pack(fill="x", padx=12, pady=10)

        # Links label
        self.sb_links_lbl = ctk.CTkLabel(
            self.sb_frame, text="LINKS",
            font=("Segoe UI", 9, "bold"), text_color=C_MUTED
        )
        self.sb_links_lbl.pack(anchor="w", padx=16, pady=(0, 6))

        links = [
            ("⚡ CurseForge", C_GOLD,
             "https://www.curseforge.com/wow/search?page=1&pageSize=20&sortBy=relevancy&search=DIEOUWE"),
            ("💬 Discord",    C_DISCORD,  "https://discord.gg/y8Pu5qsEbQ"),
            ("🌐 dieouwe.nl", C_TEXT,     "https://www.dieouwe.nl"),
            ("⚔️ Slayer Alliance", C_TEXT, "https://www.slayeralliance.com"),
            ("📦 GitHub",     C_TEXT,     "https://github.com/Die0uwe/cursebot"),
        ]
        for label, color, url in links:
            btn = ctk.CTkButton(
                self.sb_frame, text=f"  {label}",
                font=("Segoe UI", 11), anchor="w",
                fg_color="transparent", hover_color=C_BG2,
                text_color=color, height=28, corner_radius=4,
                command=lambda u=url: webbrowser.open(u)
            )
            btn.pack(fill="x", padx=8, pady=1)

    # ── MAIN CONTENT (tab systeem) ─────────────────────────────────────────────
    def _build_main(self):
        self.main_frame = ctk.CTkFrame(self.body_frame, fg_color=C_BG, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.tab_frames = {}
        for tab_id in ["dashboard", "addons", "search", "watchlist", "stats", "settings"]:
            frame = ctk.CTkScrollableFrame(
                self.main_frame, fg_color=C_BG, corner_radius=0,
                scrollbar_button_color=C_BG3
            )
            frame.grid(row=0, column=0, sticky="nsew")
            frame.grid_remove()
            self.tab_frames[tab_id] = frame

        self._build_tab_dashboard()
        self._build_tab_addons()
        self._build_tab_search()
        self._build_tab_watchlist()
        self._build_tab_stats()
        self._build_tab_settings()

        self.tab_frames["dashboard"].grid()

    def _switch_tab(self, tab_id: str):
        for t, frame in self.tab_frames.items():
            frame.grid_remove()
        self.tab_frames[tab_id].grid()
        self._active_tab = tab_id

        for t, btn in self.sb_nav_btns.items():
            if t == tab_id:
                btn.configure(fg_color=C_GOLD, text_color="#000000")
            else:
                btn.configure(fg_color="transparent", text_color=C_TEXT)

        if tab_id == "watchlist":
            self._load_watchlist_tab()
        if tab_id == "addons":
            self._load_addons_tab()
        if tab_id == "stats":
            self._load_stats_tab()

    # ── TAB: DASHBOARD (wid: dash_*) ──────────────────────────────────────────
    def _build_tab_dashboard(self):
        f = self.tab_frames["dashboard"]

        # Stat cards grid
        self.dash_stats_frame = ctk.CTkFrame(f, fg_color="transparent")
        self.dash_stats_frame.pack(fill="x", padx=16, pady=(16, 8))

        stat_defs = [
            ("dash_stat_uptime",   "Uptime",         "–",   C_GREEN),
            ("dash_stat_guilds",   "Servers",         "–",   C_GOLD),
            ("dash_stat_addons",   "Mijn addons",     "–",   C_BLUE),
            ("dash_stat_watchlist","Watchlist",        "–",   C_PURPLE),
            ("dash_stat_releases", "Releases",         "–",   C_GOLD),
            ("dash_stat_interval", "Interval",         "–",   C_TEXT),
            ("dash_stat_lastcheck","Laatste check",    "–",   C_TEXT),
            ("dash_stat_nextcheck","Volgende check",   "–",   C_TEXT),
        ]
        self.dash_stat_vals = {}
        for i, (wid, label, init, color) in enumerate(stat_defs):
            card = ctk.CTkFrame(
                self.dash_stats_frame, fg_color=C_BG2,
                corner_radius=8, border_width=1, border_color=C_BORDER
            )
            card.grid(row=i//4, column=i%4, padx=4, pady=4, sticky="ew")
            self.dash_stats_frame.grid_columnconfigure(i%4, weight=1)

            ctk.CTkLabel(
                card, text=label,
                font=("Segoe UI", 12, "bold"), text_color=C_MUTED
            ).pack(anchor="w", padx=10, pady=(12, 0))

            val_lbl = ctk.CTkLabel(
                card, text=init,
                font=("Consolas", 24, "bold"), text_color=color
            )
            val_lbl.pack(anchor="w", padx=10, pady=(2, 14))
            self.dash_stat_vals[wid] = val_lbl

        # Live log
        self.dash_log_frame = ctk.CTkFrame(f, fg_color=C_BG2, corner_radius=8, border_width=1, border_color=C_BORDER)
        self.dash_log_frame.pack(fill="x", padx=16, pady=8)

        ctk.CTkLabel(
            self.dash_log_frame, text="Live log",
            font=("Segoe UI", 10, "bold"), text_color=C_MUTED
        ).pack(anchor="w", padx=12, pady=(8, 4))

        self.dash_log_box = ctk.CTkTextbox(
            self.dash_log_frame, fg_color="#060810",
            font=FONT_MONO_SM, text_color=C_TEXT,
            height=220, state="disabled",
            border_width=0, corner_radius=6
        )
        self.dash_log_box.pack(fill="x", padx=8, pady=(0, 8))

    # ── TAB: MIJN ADDONS (wid: addons_*) ──────────────────────────────────────
    def _build_tab_addons(self):
        f = self.tab_frames["addons"]

        self.addons_header_lbl = ctk.CTkLabel(
            f, text="Mijn addons (dieouwe)",
            font=FONT_TITLE, text_color=C_TEXT
        )
        self.addons_header_lbl.pack(anchor="w", padx=16, pady=(16, 8))

        self.addons_list_frame = ctk.CTkFrame(f, fg_color="transparent")
        self.addons_list_frame.pack(fill="x", padx=16)

        self.addons_empty_lbl = ctk.CTkLabel(
            f, text="Bot offline of geen addons geladen...",
            font=FONT_BODY, text_color=C_MUTED
        )
        self.addons_empty_lbl.pack(pady=40)

    def _load_addons_tab(self):
        # Wis bestaande items
        for w in self.addons_list_frame.winfo_children():
            w.destroy()

        projects = self._stats.get("projects", [])
        if not projects:
            self.addons_empty_lbl.pack(pady=40)
            return

        self.addons_empty_lbl.pack_forget()
        for p in projects:
            self._make_addon_row(self.addons_list_frame, p, show_add=True)

    def _make_addon_row(self, parent, addon: dict, show_add: bool = False):
        row = ctk.CTkFrame(
            parent, fg_color=C_BG2, corner_radius=8,
            border_width=1, border_color=C_BORDER
        )
        row.pack(fill="x", pady=3)

        # ── Thumbnail (zelfde aanpak als CF Browser) ───────────────────────────
        # Thumbnail async — placeholder direct, image zodra geladen
        logo_url = addon.get("logo_url", "")
        thumb_frame = ctk.CTkFrame(row, fg_color=C_BG3, width=54, height=54,
                                   corner_radius=6)
        thumb_frame.pack(side="left", padx=(10, 10), pady=8)
        thumb_frame.pack_propagate(False)
        ctk.CTkLabel(thumb_frame, text="⚡", font=("Segoe UI", 22),
                     text_color=C_GOLD).pack(expand=True)
        if logo_url:
            _load_image_async([thumb_frame], logo_url, size=(54, 54), app_ref=self)

        # ── Info ───────────────────────────────────────────────────────────────
        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, pady=8)

        ctk.CTkLabel(
            info, text=addon.get("name", "?"),
            font=FONT_BODY, text_color=C_TEXT, anchor="w"
        ).pack(anchor="w")

        dl     = addon.get("downloads", 0)
        author = addon.get("author_name", "") or "dieouwe"
        # K/M formattering
        dl_str = (f"{dl/1_000_000:.1f}M" if dl >= 1_000_000
                  else f"{dl/1_000:.1f}K" if dl >= 1_000
                  else str(dl))
        ctk.CTkLabel(
            info, text=f"{author} · {dl_str} downloads",
            font=FONT_MONO_SM, text_color=C_MUTED, anchor="w"
        ).pack(anchor="w")

        # Summary indien beschikbaar
        summary = addon.get("summary", "")
        if summary:
            ctk.CTkLabel(
                info,
                text=summary[:100] + "..." if len(summary) > 100 else summary,
                font=("Segoe UI", 11), text_color=C_MUTED,
                anchor="w", wraplength=500, justify="left"
            ).pack(anchor="w", pady=(1, 0))

        # ── Knoppen ────────────────────────────────────────────────────────────
        url = addon.get("url", "")
        if url:
            ctk.CTkButton(
                row, text="CF ↗", font=FONT_SMALL,
                width=52, height=28,
                fg_color="transparent", hover_color=C_BG3,
                border_color=C_BLUE, border_width=1, text_color=C_BLUE,
                corner_radius=6,
                command=lambda u=url: webbrowser.open(u)
            ).pack(side="right", padx=(4, 8), pady=8)

        if show_add:
            ctk.CTkButton(
                row, text="+ Watch", font=FONT_SMALL,
                width=72, height=28,
                fg_color="transparent", hover_color=C_BG3,
                border_color=C_GREEN, border_width=1, text_color=C_GREEN,
                corner_radius=6,
                command=lambda a=addon: (self._add_to_watchlist(a),
                                         self._toast(f"✓ {a.get('name','?')} toegevoegd"))
            ).pack(side="right", padx=(0, 4), pady=8)

    # ── TAB: CF BROWSER ───────────────────────────────────────────────────────
    def _build_tab_browser(self):
        """Ingebouwde CurseForge browser — zoek en bekijk addons, voeg toe aan watchlist."""
        f = self.tab_frames["browser"]

        hdr = ctk.CTkFrame(f, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(hdr, text="CF Browser",
                     font=FONT_TITLE, text_color=C_TEXT).pack(side="left")
        ctk.CTkLabel(hdr, text="Zoek addons en voeg toe aan watchlist",
                     font=FONT_SMALL, text_color=C_MUTED).pack(side="left", padx=(12,0), pady=(4,0))

        # Zoekbalk
        search_row = ctk.CTkFrame(f, fg_color=C_BG2,
                                   border_width=1, border_color=C_BORDER, corner_radius=8)
        search_row.pack(fill="x", padx=16, pady=(0, 8))

        self.browser_entry = ctk.CTkEntry(
            search_row, placeholder_text="Zoek op naam, auteur of keyword...",
            font=FONT_BODY, fg_color="transparent", border_width=0,
            text_color=C_TEXT, placeholder_text_color=C_MUTED, height=40
        )
        self.browser_entry.pack(side="left", fill="x", expand=True, padx=(12, 0))
        self.browser_entry.bind("<Return>", lambda e: self._browser_search())

        self.browser_btn = ctk.CTkButton(
            search_row, text="Zoeken",
            font=FONT_SMALL, width=90, height=32,
            fg_color=C_GOLD, hover_color=C_GOLD_DIM,
            text_color="#000000", corner_radius=6,
            command=self._browser_search
        )
        self.browser_btn.pack(side="right", padx=8, pady=4)

        # Snelknoppen
        quick = ctk.CTkFrame(f, fg_color="transparent")
        quick.pack(fill="x", padx=16, pady=(0, 10))
        ctk.CTkLabel(quick, text="Snel:", font=FONT_SMALL, text_color=C_MUTED).pack(side="left")
        for term in ["dieouwe", "delvetracker", "weakauras", "details", "elvui"]:
            ctk.CTkButton(
                quick, text=term, font=("Segoe UI", 10), height=24, width=82,
                fg_color=C_BG3, hover_color=C_BG2, text_color=C_MUTED,
                border_width=1, border_color=C_BORDER, corner_radius=4,
                command=lambda t=term: self._browser_quick(t)
            ).pack(side="left", padx=(5, 0))

        self.browser_status = ctk.CTkLabel(
            f, text="Voer een zoekterm in om te beginnen.",
            font=FONT_SMALL, text_color=C_MUTED
        )
        self.browser_status.pack(anchor="w", padx=16, pady=(0, 6))

        self.browser_results = ctk.CTkScrollableFrame(
            f, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=C_BG3, height=420
        )
        self.browser_results.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    def _load_browser_tab(self):
        """Laad browser tab — vul eigen addons als standaard."""
        if not self.browser_entry.get():
            self.browser_entry.insert(0, "dieouwe")
            self._browser_search()

    def _browser_quick(self, term: str):
        self.browser_entry.delete(0, "end")
        self.browser_entry.insert(0, term)
        self._browser_search()

    def _browser_search(self):
        query = self.browser_entry.get().strip()
        if not query:
            return
        self.browser_status.configure(text=f"Zoeken naar '{query}'...", text_color=C_MUTED)
        self.browser_btn.configure(state="disabled", text="...")
        for w in self.browser_results.winfo_children():
            w.destroy()

        def task():
            results = []

            # ── Methode 1: directe CF API aanroep (werkt ook als bot offline is)
            try:
                from bot.services.key_manager import get_key
                cf_key = get_key("CURSEFORGE_API_KEY")
                if cf_key:
                    import urllib.request, urllib.parse, json as _json
                    params = urllib.parse.urlencode({
                        "gameId": 1,
                        "searchFilter": query,
                        "pageSize": 10,
                        "sortField": 6,
                        "sortOrder": "desc",
                    })
                    req = urllib.request.Request(
                        f"https://api.curseforge.com/v1/mods/search?{params}",
                        headers={"x-api-key": cf_key, "Accept": "application/json"},
                    )
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = _json.loads(resp.read())
                    for p in data.get("data", []):
                        authors = p.get("authors", [])
                        logo    = (p.get("logo") or {}).get("thumbnailUrl", "")
                        results.append({
                            "id":          p["id"],
                            "name":        p["name"],
                            "slug":        p["slug"],
                            "summary":     p.get("summary", ""),
                            "url":         (p.get("links") or {}).get("websiteUrl", ""),
                            "downloads":   p.get("downloadCount", 0),
                            "logo_url":    logo,
                            "author_name": authors[0].get("name","") if authors else "",
                        })
            except Exception:
                pass

            # ── Methode 2: via bot Flask API (fallback als bot online is)
            if not results:
                try:
                    q_enc = urllib.parse.quote(query)
                    data  = api_get(f"/api/cf/search?q={q_enc}", timeout=8)
                    if data and data.get("results"):
                        results = data["results"]
                except Exception:
                    pass

            # ── Methode 3: zoek in eigen project_list (laatste fallback)
            if not results:
                try:
                    stats = api_get("/api/stats", timeout=5)
                    if stats:
                        q = query.lower()
                        results = [
                            p for p in stats.get("projects", [])
                            if q in p.get("name","").lower()
                            or q in p.get("slug","").lower()
                        ]
                except Exception:
                    pass

            self.after(0, lambda: self._browser_show(results, query))

        threading.Thread(target=task, daemon=True).start()

    def _browser_show(self, results: list, query: str):
        self.browser_btn.configure(state="normal", text="Zoeken")
        for w in self.browser_results.winfo_children():
            w.destroy()

        if not results:
            self.browser_status.configure(
                text=f"Geen resultaten voor '{query}'. Bot moet online zijn voor CF zoekopdrachten.",
                text_color=C_MUTED
            )
            ctk.CTkButton(
                self.browser_results,
                text=f"Zoek '{query}' op CurseForge.com ↗",
                font=FONT_SMALL, height=32, width=300,
                fg_color="transparent", hover_color=C_BG2,
                text_color=C_BLUE, border_width=1, border_color=C_BLUE,
                command=lambda: webbrowser.open(
                    f"https://www.curseforge.com/wow/search?page=1&search={query}"
                )
            ).pack(anchor="w", pady=8)
            return

        self.browser_status.configure(
            text=f"{len(results)} resultaten voor '{query}'", text_color=C_GREEN
        )
        for addon in results:
            self._browser_row(addon)

    def _browser_row(self, addon: dict):
        row = ctk.CTkFrame(self.browser_results, fg_color=C_BG2,
                            corner_radius=8, border_width=1, border_color=C_BORDER)
        row.pack(fill="x", pady=3)

        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=10)

        # ── Thumbnail async ────────────────────────────────────────────────────
        logo_url = addon.get("logo_url", "")
        br_thumb = ctk.CTkFrame(inner, fg_color=C_BG3, width=52, height=52,
                                corner_radius=6)
        br_thumb.pack(side="left", padx=(0, 10))
        br_thumb.pack_propagate(False)
        ctk.CTkLabel(br_thumb, text="📦", font=("Segoe UI", 20),
                     text_color=C_MUTED).pack(expand=True)
        if logo_url:
            _load_image_async([br_thumb], logo_url, size=(52, 52), app_ref=self)

        # ── Info kolom ─────────────────────────────────────────────────────────
        info = ctk.CTkFrame(inner, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)

        # Naam + game version badge
        name_row = ctk.CTkFrame(info, fg_color="transparent")
        name_row.pack(fill="x", anchor="w")
        ctk.CTkLabel(name_row, text=addon.get("name", "Onbekend"),
                     font=FONT_BODY, text_color=C_TEXT, anchor="w").pack(side="left")

        gv = addon.get("game_versions")
        if gv:
            ver = gv[0] if isinstance(gv, list) else str(gv)
            ctk.CTkLabel(
                name_row, text=f" {ver}",
                font=("Segoe UI", 9), text_color=C_MUTED,
                fg_color=C_BG3, corner_radius=4,
                padx=5, pady=1
            ).pack(side="left", padx=(6, 0))

        # Auteur + downloads
        meta = []
        if addon.get("author_name"):
            meta.append(f"door {addon['author_name']}")
        dl = addon.get("downloads", 0)
        if dl:
            # K-formattering: 1500 → 1.5K, 1200000 → 1.2M
            if dl >= 1_000_000:
                meta.append(f"{dl/1_000_000:.1f}M dl")
            elif dl >= 1_000:
                meta.append(f"{dl/1_000:.1f}K dl")
            else:
                meta.append(f"{dl} dl")
        if meta:
            ctk.CTkLabel(info, text=" · ".join(meta),
                         font=FONT_SMALL, text_color=C_MUTED,
                         anchor="w").pack(anchor="w")

        summary = addon.get("summary", "")
        if summary:
            ctk.CTkLabel(
                info,
                text=summary[:120] + "..." if len(summary) > 120 else summary,
                font=("Segoe UI", 11), text_color=C_MUTED,
                anchor="w", wraplength=500, justify="left"
            ).pack(anchor="w", pady=(2, 0))

        # ── Knoppen rechts ─────────────────────────────────────────────────────
        btns = ctk.CTkFrame(inner, fg_color="transparent")
        btns.pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btns, text="+ Watch",
            font=FONT_SMALL, width=82, height=30,
            fg_color=C_GOLD, hover_color=C_GOLD_DIM,
            text_color="#000000", corner_radius=6,
            command=lambda a=addon: (self._add_to_watchlist(a),
                                     self._toast(f"✓ {a.get('name','?')} toegevoegd"))
        ).pack(pady=(0, 4))

        if addon.get("url"):
            ctk.CTkButton(
                btns, text="CF ↗",
                font=FONT_SMALL, width=82, height=30,
                fg_color="transparent", hover_color=C_BG3,
                text_color=C_BLUE, border_width=1, border_color=C_BLUE,
                corner_radius=6,
                command=lambda u=addon["url"]: webbrowser.open(u)
            ).pack()

    # ── TAB: ZOEKEN (wid: search_*) ───────────────────────────────────────────
    def _build_tab_search(self):
        f = self.tab_frames["search"]

        ctk.CTkLabel(
            f, text="Addon zoeken",
            font=FONT_TITLE, text_color=C_TEXT
        ).pack(anchor="w", padx=16, pady=(16, 8))

        search_bar = ctk.CTkFrame(f, fg_color=C_BG2, corner_radius=8, border_width=1, border_color=C_BORDER)
        search_bar.pack(fill="x", padx=16, pady=(0, 8))

        inner = ctk.CTkFrame(search_bar, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=10)

        self.search_entry = ctk.CTkEntry(
            inner, placeholder_text="🔍  Naam, auteur of CF project ID...",
            font=FONT_BODY, fg_color=C_BG3, border_color=C_BORDER,
            text_color=C_TEXT, placeholder_text_color=C_MUTED,
            height=36
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.search_entry.bind("<Return>", lambda e: self._do_search())

        self.search_btn = ctk.CTkButton(
            inner, text="Zoeken", font=FONT_BODY,
            width=80, height=36,
            fg_color=C_GOLD, hover_color="#d4891e", text_color="#000000",
            command=self._do_search
        )
        self.search_btn.pack(side="left")

        self.search_id_btn = ctk.CTkButton(
            inner, text="Op ID", font=FONT_BODY,
            width=64, height=36,
            fg_color="transparent", hover_color=C_BG3,
            border_color=C_BLUE, border_width=1, text_color=C_BLUE,
            command=self._do_search_by_id
        )
        self.search_id_btn.pack(side="left", padx=(6, 0))

        # Filters
        filter_row = ctk.CTkFrame(search_bar, fg_color="transparent")
        filter_row.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkLabel(filter_row, text="Filter:", font=FONT_SMALL, text_color=C_MUTED).pack(side="left", padx=(0,6))

        self.search_filter_var = ctk.StringVar(value="all")
        for val, label in [("all","Alles"), ("stable","Stable"), ("stable_beta","Stable+Beta")]:
            ctk.CTkRadioButton(
                filter_row, text=label,
                font=FONT_SMALL, text_color=C_TEXT,
                variable=self.search_filter_var, value=val,
                fg_color=C_GOLD
            ).pack(side="left", padx=8)

        # Resultaten
        self.search_status_lbl = ctk.CTkLabel(
            f, text="", font=FONT_SMALL, text_color=C_MUTED
        )
        self.search_status_lbl.pack(anchor="w", padx=16, pady=(0, 4))

        self.search_results_frame = ctk.CTkFrame(f, fg_color="transparent")
        self.search_results_frame.pack(fill="x", padx=16)

    def _do_search(self):
        query = self.search_entry.get().strip()
        if not query:
            return
        self.search_status_lbl.configure(text=f"Zoeken naar '{query}'...")
        self.search_btn.configure(state="disabled")

        def task():
            # Probeer eerst via bot API, fallback naar web
            results = api_get(f"/api/cf/search?q={urllib.parse.quote(query)}")
            if results and results.get("results"):
                data = results["results"]
            else:
                data = cf_search_web(query)
            self.after(0, lambda: self._show_search_results(data, query))

        threading.Thread(target=task, daemon=True).start()

    def _do_search_by_id(self):
        query = self.search_entry.get().strip()
        if not query.isdigit():
            self.search_status_lbl.configure(text="Voer een numeriek CF project ID in")
            return
        self.search_status_lbl.configure(text=f"Ophalen ID {query}...")
        self.search_btn.configure(state="disabled")

        def task():
            try:
                url = f"https://api.curseforge.com/v1/mods/{query}"
                # Zonder API key — probeer via bot API
                result = api_get(f"/api/cf/addon/{query}")
                if result:
                    self.after(0, lambda: self._show_search_results([result], query))
                else:
                    self.after(0, lambda: self.search_status_lbl.configure(
                        text="Start de bot voor live CF data"
                    ))
            except Exception as e:
                self.after(0, lambda: self.search_status_lbl.configure(text=str(e)))
            finally:
                self.after(0, lambda: self.search_btn.configure(state="normal"))

        threading.Thread(target=task, daemon=True).start()

    def _show_search_results(self, data: list, query: str):
        for w in self.search_results_frame.winfo_children():
            w.destroy()
        self.search_btn.configure(state="normal")

        if not data:
            self.search_status_lbl.configure(text=f"Geen resultaten voor '{query}'")
            return

        self.search_status_lbl.configure(text=f"{len(data)} resultaten voor '{query}'")
        for item in data[:10]:
            # Normaliseer CF API response
            if isinstance(item, dict):
                authors = item.get("authors", [])
                author  = authors[0].get("name","") if authors else ""
                addon   = {
                    "id":          item.get("id", 0),
                    "name":        item.get("name","?"),
                    "author_name": author,
                    "downloads":   item.get("downloadCount", 0),
                    "url":         (item.get("links") or {}).get("websiteUrl",""),
                    "summary":     item.get("summary",""),
                    "addon_slug":  item.get("slug",""),
                    "logo_url":    (item.get("logo") or {}).get("thumbnailUrl"),
                    "release_filter": self.search_filter_var.get(),
                }
                self._make_search_result_row(addon)

    def _make_search_result_row(self, addon: dict):
        row = ctk.CTkFrame(
            self.search_results_frame, fg_color=C_BG2,
            corner_radius=8, border_width=1, border_color=C_BORDER
        )
        row.pack(fill="x", pady=3)

        ctk.CTkLabel(
            row, text="⚡", font=("Segoe UI", 16), text_color=C_GOLD, width=32
        ).pack(side="left", padx=(10, 4), pady=8)

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, pady=6)

        ctk.CTkLabel(
            info, text=addon["name"],
            font=FONT_BODY, text_color=C_TEXT, anchor="w"
        ).pack(anchor="w")

        ctk.CTkLabel(
            info, text=f"{addon['author_name']} · {addon['downloads']:,} downloads · ID: {addon['id']}",
            font=FONT_MONO_SM, text_color=C_MUTED, anchor="w"
        ).pack(anchor="w")

        if addon.get("url"):
            ctk.CTkButton(
                row, text="CF ↗", font=FONT_SMALL, width=48, height=26,
                fg_color="transparent", hover_color=C_BG3,
                border_color=C_BLUE, border_width=1, text_color=C_BLUE,
                command=lambda u=addon["url"]: webbrowser.open(u)
            ).pack(side="right", padx=(4, 4), pady=8)

        ctk.CTkButton(
            row, text="+ Watch", font=FONT_SMALL, width=64, height=26,
            fg_color="transparent", hover_color=C_BG3,
            border_color=C_GREEN, border_width=1, text_color=C_GREEN,
            command=lambda a=addon: self._add_to_watchlist(a)
        ).pack(side="right", padx=(0, 4), pady=8)

    # ── TAB: WATCHLIST (wid: wl_*) ────────────────────────────────────────────
    def _build_tab_watchlist(self):
        f = self.tab_frames["watchlist"]

        hdr = ctk.CTkFrame(f, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(
            hdr, text="Watchlist",
            font=FONT_TITLE, text_color=C_TEXT
        ).pack(side="left")

        self.wl_count_lbl = ctk.CTkLabel(
            hdr, text="", font=FONT_SMALL, text_color=C_MUTED
        )
        self.wl_count_lbl.pack(side="left", padx=10)

        ctk.CTkButton(
            hdr, text="↺ Verversen", font=FONT_SMALL, width=88, height=28,
            fg_color="transparent", hover_color=C_BG3,
            border_color=C_BLUE, border_width=1, text_color=C_BLUE,
            command=self._load_watchlist_tab
        ).pack(side="right")

        self.wl_list_frame = ctk.CTkFrame(f, fg_color="transparent")
        self.wl_list_frame.pack(fill="x", padx=16)

        self.wl_empty_lbl = ctk.CTkLabel(
            f, text="Watchlist leeg — gebruik /watch of de zoekfunctie.",
            font=FONT_BODY, text_color=C_MUTED
        )
        self.wl_empty_lbl.pack(pady=40)

    def _load_watchlist_tab(self):
        for w in self.wl_list_frame.winfo_children():
            w.destroy()

        def task():
            data = api_get(f"/api/watchlist?guild_id={self._guild_id}")
            self.after(0, lambda: self._render_watchlist(data))

        threading.Thread(target=task, daemon=True).start()

    def _render_watchlist(self, data):
        if not data or not data.get("items"):
            self.wl_empty_lbl.pack(pady=40)
            self.wl_count_lbl.configure(text="(0 addons)")
            return

        self.wl_empty_lbl.pack_forget()
        items = data["items"]
        self.wl_count_lbl.configure(text=f"({len(items)} addons)")

        filter_labels = {
            "all": "Alle releases", "stable": "Alleen Stable", "stable_beta": "Stable+Beta"
        }
        for item in items:
            row = ctk.CTkFrame(
                self.wl_list_frame, fg_color=C_BG2,
                corner_radius=8, border_width=1, border_color=C_BORDER
            )
            row.pack(fill="x", pady=3)

            # Thumbnail async
            wl_thumb = ctk.CTkFrame(row, fg_color=C_BG3, width=54, height=54,
                                    corner_radius=6)
            wl_thumb.pack(side="left", padx=(10, 10), pady=8)
            wl_thumb.pack_propagate(False)
            ctk.CTkLabel(wl_thumb, text="📋", font=("Segoe UI", 22),
                         text_color=C_MUTED).pack(expand=True)
            logo = item.get("logo_url") or item.get("addon_logo","")
            if logo:
                _load_image_async([wl_thumb], logo, size=(54, 54), app_ref=self)

            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, pady=6)

            ctk.CTkLabel(
                info, text=item["addon_name"],
                font=FONT_BODY, text_color=C_TEXT, anchor="w"
            ).pack(anchor="w")

            flt = filter_labels.get(item.get("release_filter","all"), "Alle releases")
            ctk.CTkLabel(
                info,
                text=f"{item.get('author_name','–')} · ID: {item['addon_id']} · {flt}",
                font=FONT_MONO_SM, text_color=C_MUTED, anchor="w"
            ).pack(anchor="w")

            if item.get("addon_url"):
                ctk.CTkButton(
                    row, text="CF ↗", font=FONT_SMALL, width=48, height=26,
                    fg_color="transparent", hover_color=C_BG3,
                    border_color=C_BLUE, border_width=1, text_color=C_BLUE,
                    command=lambda u=item["addon_url"]: webbrowser.open(u)
                ).pack(side="right", padx=(4, 4), pady=8)

            ctk.CTkButton(
                row, text="✕", font=FONT_SMALL, width=32, height=26,
                fg_color="transparent", hover_color=C_BG3,
                border_color=C_RED, border_width=1, text_color=C_RED,
                command=lambda i=item: self._remove_from_watchlist(i)
            ).pack(side="right", padx=(0, 4), pady=8)


    # ── TAB: STATISTIEKEN (wid: stat_*) ───────────────────────────────────────
    def _build_tab_stats(self):
        f = self.tab_frames["stats"]

        ctk.CTkLabel(
            f, text="Download statistieken",
            font=FONT_TITLE, text_color=C_TEXT
        ).pack(anchor="w", padx=16, pady=(16, 4))

        ctk.CTkLabel(
            f, text="Groei t.o.v. vorige meting",
            font=FONT_SMALL, text_color=C_MUTED
        ).pack(anchor="w", padx=16, pady=(0, 12))

        self.stat_refresh_btn = ctk.CTkButton(
            f, text="↺ Verversen", font=FONT_SMALL,
            width=88, height=28,
            fg_color="transparent", hover_color=C_BG3,
            border_color=C_BLUE, border_width=1, text_color=C_BLUE,
            command=self._load_stats_tab
        )
        self.stat_refresh_btn.pack(anchor="e", padx=16, pady=(0, 8))

        self.stats_list_frame = ctk.CTkFrame(f, fg_color="transparent")
        self.stats_list_frame.pack(fill="x", padx=16)

        self.stats_empty_lbl = ctk.CTkLabel(
            f, text="Start de bot voor statistieken...",
            font=FONT_BODY, text_color=C_MUTED
        )
        self.stats_empty_lbl.pack(pady=40)

    def _load_stats_tab(self):
        for w in self.stats_list_frame.winfo_children():
            w.destroy()

        def task():
            data = api_get("/api/stats")
            self.after(0, lambda: self._render_stats(data))
        threading.Thread(target=task, daemon=True).start()

    def _render_stats(self, data):
        if not data or not data.get("projects"):
            self.stats_empty_lbl.pack(pady=40)
            return

        self.stats_empty_lbl.pack_forget()
        projects = sorted(
            data.get("projects", []),
            key=lambda p: p.get("downloads", 0),
            reverse=True
        )

        for p in projects:
            row = ctk.CTkFrame(
                self.stats_list_frame, fg_color=C_BG2,
                corner_radius=8, border_width=1, border_color=C_BORDER
            )
            row.pack(fill="x", pady=3)

            # Thumbnail async
            st_thumb = ctk.CTkFrame(row, fg_color=C_BG3, width=54, height=54,
                                    corner_radius=6)
            st_thumb.pack(side="left", padx=(10, 10), pady=8)
            st_thumb.pack_propagate(False)
            ctk.CTkLabel(st_thumb, text="📊", font=("Segoe UI", 22),
                         text_color=C_PURPLE).pack(expand=True)
            logo = p.get("logo_url","")
            if logo:
                _load_image_async([st_thumb], logo, size=(54, 54), app_ref=self)

            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, pady=6)

            ctk.CTkLabel(
                info, text=p.get("name","?"),
                font=FONT_BODY, text_color=C_TEXT, anchor="w"
            ).pack(anchor="w")

            dl = p.get("downloads", 0)
            dl_str = (f"{dl/1_000_000:.1f}M" if dl >= 1_000_000
                      else f"{dl/1_000:.1f}K" if dl >= 1_000 else str(dl))
            ctk.CTkLabel(
                info, text=f"{dl_str} downloads",
                font=FONT_MONO_SM, text_color=C_MUTED, anchor="w"
            ).pack(anchor="w")

            # Progress bar (relatief aan hoogste)
            max_dl = max((x.get("downloads",1) for x in projects), default=1)
            pct    = min(int((dl / max_dl) * 100), 100)
            bar = ctk.CTkProgressBar(
                info, width=200, height=6,
                fg_color=C_BG3, progress_color=C_PURPLE
            )
            bar.set(pct / 100)
            bar.pack(anchor="w", pady=(3, 0))

            if p.get("url"):
                ctk.CTkButton(
                    row, text="CF ↗", font=FONT_SMALL, width=48, height=26,
                    fg_color="transparent", hover_color=C_BG3,
                    border_color=C_BLUE, border_width=1, text_color=C_BLUE,
                    command=lambda u=p["url"]: webbrowser.open(u)
                ).pack(side="right", padx=(4, 8), pady=8)

    # ── TAB: INSTELLINGEN (wid: cfg_*) ────────────────────────────────────────
    def _build_tab_settings(self):
        f = self.tab_frames["settings"]

        ctk.CTkLabel(
            f, text="Instellingen",
            font=FONT_TITLE, text_color=C_TEXT
        ).pack(anchor="w", padx=16, pady=(16, 12))

        cfg_frame = ctk.CTkFrame(f, fg_color=C_BG2, corner_radius=8, border_width=1, border_color=C_BORDER)
        cfg_frame.pack(fill="x", padx=16, pady=(0, 12))

        fields = [
            ("cfg_slug",     "CF Auteur slug",    "dieouwe"),
            ("cfg_id",       "CF Auteur ID",       "1417946"),
            ("cfg_interval", "Poll interval (min)","10"),
            ("cfg_guild",    "Guild ID (UI)",      "0"),
        ]
        self.cfg_vars = {}
        for wid, label, placeholder in fields:
            row = ctk.CTkFrame(cfg_frame, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=6)
            ctk.CTkLabel(
                row, text=label, font=FONT_SMALL, text_color=C_MUTED, width=150
            ).pack(side="left")
            var = ctk.StringVar(value="")
            entry = ctk.CTkEntry(
                row, textvariable=var,
                placeholder_text=placeholder,
                font=FONT_MONO_SM, fg_color=C_BG3,
                border_color=C_BORDER, text_color=C_TEXT,
                height=30
            )
            entry.pack(side="left", fill="x", expand=True)
            self.cfg_vars[wid] = var

        self.cfg_loglevel_var = ctk.StringVar(value="INFO")
        row = ctk.CTkFrame(cfg_frame, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(row, text="Log level", font=FONT_SMALL, text_color=C_MUTED, width=150).pack(side="left")
        ctk.CTkOptionMenu(
            row, values=["DEBUG","INFO","WARNING","ERROR"],
            variable=self.cfg_loglevel_var,
            font=FONT_SMALL, fg_color=C_BG3, text_color=C_TEXT,
            button_color=C_BG3, dropdown_fg_color=C_BG3, height=30
        ).pack(side="left")

        self.cfg_save_btn = ctk.CTkButton(
            f, text="Opslaan", font=FONT_BODY,
            fg_color=C_GOLD, hover_color="#d4891e", text_color="#000000",
            height=36, command=self._save_settings
        )
        self.cfg_save_btn.pack(anchor="w", padx=16, pady=4)

        self.cfg_status_lbl = ctk.CTkLabel(
            f, text="", font=FONT_SMALL, text_color=C_GREEN
        )
        self.cfg_status_lbl.pack(anchor="w", padx=16)

        # ── Beveiliging sectie ────────────────────────────────────────────────
        ctk.CTkLabel(
            f, text="Beveiliging",
            font=FONT_TITLE, text_color=C_TEXT
        ).pack(anchor="w", padx=16, pady=(20, 8))

        sec_frame = ctk.CTkFrame(f, fg_color=C_BG2, corner_radius=8,
                                  border_width=1, border_color=C_BORDER)
        sec_frame.pack(fill="x", padx=16, pady=(0, 8))

        # Keyring status
        sec_status_row = ctk.CTkFrame(sec_frame, fg_color="transparent")
        sec_status_row.pack(fill="x", padx=12, pady=10)

        try:
            import keyring as _kr
            _kr.get_password("CurseBot-SlayerAlliance", "_test_")
            sec_txt   = "🔒 Windows Credential Manager actief"
            sec_color = C_GREEN
        except ImportError:
            sec_txt   = "⚠ keyring niet geïnstalleerd — keys in .env (plaintext)"
            sec_color = C_GOLD
        except Exception:
            sec_txt   = "🔒 OS keyring actief"
            sec_color = C_GREEN

        ctk.CTkLabel(sec_status_row, text=sec_txt,
                     font=FONT_SMALL, text_color=sec_color,
                     anchor="w").pack(side="left")

        # Knoppen
        sec_btn_row = ctk.CTkFrame(sec_frame, fg_color="transparent")
        sec_btn_row.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkButton(
            sec_btn_row, text="API Keys bijwerken",
            font=FONT_SMALL, height=30, width=160,
            fg_color="transparent", hover_color=C_BG3,
            border_color=C_GOLD, border_width=1, text_color=C_GOLD,
            command=self._open_setup_wizard
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            sec_btn_row, text="Keys wissen",
            font=FONT_SMALL, height=30, width=120,
            fg_color="transparent", hover_color=C_BG3,
            border_color=C_RED, border_width=1, text_color=C_RED,
            command=self._clear_keys
        ).pack(side="left")

    def _clear_keys(self):
        """Verwijder alle opgeslagen keys na bevestiging."""
        from tkinter import messagebox
        if not messagebox.askyesno(
            "Keys wissen",
            "Alle opgeslagen API keys verwijderen uit Credential Manager?\n"
            "De bot kan daarna niet meer starten zonder nieuwe configuratie."
        ):
            return
        try:
            from bot.services.key_manager import delete_key, ALL_KEYS
            for k in ALL_KEYS:
                delete_key(k)
            self._toast("✓ Alle keys gewist")
        except Exception as e:
            self._toast(f"⚠ Fout: {e}")

    def _save_settings(self):
        guild = self.cfg_vars.get("cfg_guild")
        if guild:
            self._guild_id = guild.get() or "0"

        data = {
            "CF_AUTHOR_SLUG":         self.cfg_vars["cfg_slug"].get(),
            "CF_AUTHOR_ID":           self.cfg_vars["cfg_id"].get(),
            "CHECK_INTERVAL_MINUTES": self.cfg_vars["cfg_interval"].get(),
            "LOG_LEVEL":              self.cfg_loglevel_var.get(),
        }
        result = api_post("/api/settings", {k: v for k, v in data.items() if v})
        if result:
            self.cfg_status_lbl.configure(text="✓ Opgeslagen — herstart bot om te activeren", text_color=C_GREEN)
        else:
            self.cfg_status_lbl.configure(text="⚠ Bot offline — instellingen lokaal niet opgeslagen", text_color=C_GOLD)

    # ── FOOTER (wid: ftr_*) ───────────────────────────────────────────────────
    def _build_footer(self):
        self.ftr_frame = ctk.CTkFrame(
            self, fg_color=C_BG3, corner_radius=0, height=30,
            border_width=1, border_color=C_BORDER
        )
        self.ftr_frame.pack(fill="x", side="bottom")
        self.ftr_frame.pack_propagate(False)

        self.ftr_version_lbl = ctk.CTkLabel(
            self.ftr_frame, text="CurseBot v2.0",
            font=("Segoe UI", 9), text_color=C_MUTED
        )
        self.ftr_version_lbl.pack(side="left", padx=12)

        self.ftr_sha_lbl = ctk.CTkLabel(
            self.ftr_frame, text="",
            font=("Consolas", 9), text_color=C_MUTED
        )
        self.ftr_sha_lbl.pack(side="left", padx=(0, 12))

        for label, url in [
            ("dieouwe.nl", "https://www.dieouwe.nl"),
            ("discord.gg/y8Pu5qsEbQ", "https://discord.gg/y8Pu5qsEbQ"),
        ]:
            ctk.CTkButton(
                self.ftr_frame, text=label,
                font=("Segoe UI", 9), text_color=C_MUTED,
                fg_color="transparent", hover_color=C_BG2,
                height=24, width=10,
                command=lambda u=url: webbrowser.open(u)
            ).pack(side="right", padx=4)

    # ── WATCHLIST ACTIES ───────────────────────────────────────────────────────
    def _add_to_watchlist(self, addon: dict):
        data = {
            "guild_id":       self._guild_id,
            "addon_id":       addon.get("id"),
            "addon_name":     addon.get("name",""),
            "addon_slug":     addon.get("slug","") or addon.get("addon_slug",""),
            "addon_url":      addon.get("url",""),
            "author_name":    addon.get("author_name",""),
            "downloads":      addon.get("downloads", 0),
            "logo_url":       addon.get("logo_url"),
            "release_filter": addon.get("release_filter", "all"),
        }
        def task():
            result = api_post("/api/watchlist/add", data)
            if result:
                msg = f"✓ {addon.get('name')} toegevoegd!" if result.get("added") else f"Al in watchlist: {addon.get('name')}"
            else:
                msg = "⚠ Bot offline — gebruik /watch in Discord"
            self.after(0, lambda: self._toast(msg))
        threading.Thread(target=task, daemon=True).start()

    def _remove_from_watchlist(self, item: dict):
        if not messagebox.askyesno(
            "Verwijderen",
            f"'{item['addon_name']}' uit watchlist verwijderen?"
        ):
            return
        data = {"guild_id": self._guild_id, "addon_id": item["addon_id"]}
        def task():
            result = api_post("/api/watchlist/remove", data)
            self.after(0, self._load_watchlist_tab)
            self.after(0, lambda: self._toast(
                f"✓ {item['addon_name']} verwijderd" if result else "⚠ Bot offline"
            ))
        threading.Thread(target=task, daemon=True).start()

    # ── ACTIES ─────────────────────────────────────────────────────────────────
    def _do_check(self):
        def task():
            api_post("/api/check", {})
            self.after(0, lambda: self._toast("↺ CF check getriggerd"))
        threading.Thread(target=task, daemon=True).start()

    def _do_stop(self):
        if not messagebox.askyesno("Bot stoppen", "Bot stoppen? Hij stopt na de huidige actie."):
            return
        def task():
            # Primair: via BotManager (betrouwbaarder dan API call)
            stopped = False
            if self._bot_manager:
                stopped = self._bot_manager.stop()

            # Fallback: via Flask /api/stop als BotManager niet beschikbaar
            if not stopped:
                result = api_post("/api/stop", {})
                stopped = bool(result and result.get("ok"))

            if stopped:
                self.after(0, lambda: self._toast("⏹ Bot gestopt"))
                self.after(0, lambda: self._update_start_stop_buttons(online=False))
            else:
                self.after(0, lambda: self._toast("⚠ Bot offline of kon niet stoppen"))
        threading.Thread(target=task, daemon=True).start()

    def _do_start(self):
        """Herstart de bot via BotManager zonder de app te sluiten."""
        if self._bot_manager is None:
            self._toast("⚠ BotManager niet beschikbaar — herstart de app handmatig")
            return
        if self._bot_manager.is_running:
            self._toast("⚠ Bot draait al")
            return

        def task():
            self.after(0, lambda: self._toast("▶ Bot wordt gestart..."))
            self.after(0, lambda: self._update_start_stop_buttons(starting=True))
            try:
                ok = self._bot_manager.start()
                if ok:
                    # Wacht kort zodat bot kan initialiseren
                    import time; time.sleep(3)
                    self.after(0, lambda: self._toast("✓ Bot gestart"))
                else:
                    self.after(0, lambda: self._toast("⚠ Bot kon niet starten"))
                    self.after(0, lambda: self._update_start_stop_buttons(online=False))
            except Exception as e:
                self.after(0, lambda: self._toast(f"✗ Fout: {e}"))
                self.after(0, lambda: self._update_start_stop_buttons(online=False))
        threading.Thread(target=task, daemon=True).start()

    def _update_start_stop_buttons(self, online: bool = False, starting: bool = False):
        """Wissel zichtbaarheid Start/Stop knop op basis van bot-state."""
        try:
            if starting:
                # Tijdens opstarten: beide verborgen, status toont "Starten..."
                self.hdr_start_btn.pack_forget()
                self.hdr_stop_btn.pack_forget()
                self.hdr_status_dot.configure(text_color=C_GOLD)
                self.hdr_status_lbl.configure(text="Starten...", text_color=C_GOLD)
            elif online:
                # Bot online: Stop zichtbaar, Start verborgen
                self.hdr_start_btn.pack_forget()
                self.hdr_stop_btn.pack(side="right", padx=(0, 6), pady=10)
                self.hdr_status_dot.configure(text_color=C_GREEN)
                self.hdr_status_lbl.configure(text="Online", text_color=C_GREEN)
            else:
                # Bot offline: Start zichtbaar, Stop verborgen
                self.hdr_stop_btn.pack_forget()
                self.hdr_start_btn.pack(side="right", padx=(0, 6), pady=10)
                self.hdr_status_dot.configure(text_color=C_RED)
                self.hdr_status_lbl.configure(text="Offline", text_color=C_RED)
        except Exception:
            pass  # Widget al vernietigd bij afsluiten

    def _do_update(self):
        def task():
            result = api_post("/api/update", {})
            if result:
                msg = "✓ Bot bijgewerkt!" if result.get("updated") else "✓ Al up-to-date"
            else:
                msg = "⚠ Bot offline"
            self.after(0, lambda: self._toast(msg))
        threading.Thread(target=task, daemon=True).start()

    def _do_reset(self):
        if not messagebox.askyesno("Cache reset", "File ID cache wissen?"):
            return
        def task():
            api_post("/api/reset", {})
            self.after(0, lambda: self._toast("✓ Cache gewist"))
        threading.Thread(target=task, daemon=True).start()

    # ── POLL & REFRESH ─────────────────────────────────────────────────────────
    def _start_poll(self):
        def poll():
            while self._poll_active:
                try:
                    data = api_get("/api/stats", timeout=3)
                    if data:
                        self._stats      = data
                        self._bot_online = data.get("bot_online", False)
                    else:
                        self._bot_online = False
                    self.after(0, self._refresh)
                except Exception:
                    pass
                import time; time.sleep(5)
        threading.Thread(target=poll, daemon=True).start()

    def _refresh(self):
        d = self._stats

        # Header status + Start/Stop knop synchronisatie
        if self._bot_online:
            self._update_start_stop_buttons(online=True)
        else:
            # Alleen offline tonen als we niet midden in een start zitten
            status_text = self.hdr_status_lbl.cget("text")
            if status_text != "Starten...":
                self._update_start_stop_buttons(online=False)

        self.hdr_uptime_lbl.configure(text=d.get("uptime",""))

        # Footer sha
        sha = d.get("last_update_sha","")
        if sha and sha != "onbekend":
            self.ftr_sha_lbl.configure(text=f"commit {sha[:8]}")

        # Stat cards
        # Watchlist count: uit STATS (alle guilds) of fallback naar lokale cache
        wl_count = d.get("watchlist_count")
        if wl_count is None:
            wl_count = len(self._watchlist) if self._watchlist else "–" 
        vals = {
            "dash_stat_uptime":    d.get("uptime","–"),
            "dash_stat_guilds":    str(d.get("guilds","–")),
            "dash_stat_addons":    str(d.get("projects_tracked","–")),
            "dash_stat_watchlist": str(wl_count),
            "dash_stat_releases":  str(d.get("releases_detected","–")),
            "dash_stat_interval":  f"{d.get('check_interval','–')} min",
            "dash_stat_lastcheck": d.get("last_check","–"),
            "dash_stat_nextcheck": d.get("next_check","–"),
        }
        for wid, val in vals.items():
            if wid in self.dash_stat_vals:
                self.dash_stat_vals[wid].configure(text=val)

        # Log — kleur-coded per prefix
        lines = d.get("log_lines", [])
        if lines:
            self.dash_log_box.configure(state="normal")
            self.dash_log_box.delete("1.0", "end")

            # Tag kleuren definiëren (alleen bij eerste keer)
            try:
                self.dash_log_box.tag_config("err",  foreground="#e74c3c")  # rood
                self.dash_log_box.tag_config("warn", foreground="#f5a623")  # goud
                self.dash_log_box.tag_config("cf",   foreground="#f5a623")  # goud
                self.dash_log_box.tag_config("bot",  foreground="#3d9eff")  # blauw
                self.dash_log_box.tag_config("ok",   foreground="#2ecc71")  # groen
                self.dash_log_box.tag_config("dim",  foreground="#4a5568")  # grijs
            except Exception:
                pass

            for line in lines[-40:]:
                lu = line.upper()
                if "[ERROR]" in lu or "✗" in line or "FOUT" in lu:
                    tag = "err"
                elif "[WARNING]" in lu or "⚠" in line or "WAF" in lu:
                    tag = "warn"
                elif "[CF]" in line:
                    tag = "cf"
                elif "[BOT]" in line:
                    tag = "bot"
                elif "✓" in line or "ONLINE" in lu or "GELADEN" in lu:
                    tag = "ok"
                elif "[DEBUG]" in lu:
                    tag = "dim"
                else:
                    tag = None

                if tag:
                    self.dash_log_box.insert("end", line + "\n", tag)
                else:
                    self.dash_log_box.insert("end", line + "\n")

            self.dash_log_box.see("end")
            self.dash_log_box.configure(state="disabled")

    def _copy_invite_link(self):
        """Kopieer de invite URL naar klembord en open in browser."""
        data = api_get("/api/stats")
        # Gebruik bekende permission integer
        perm_int = 67464256
        # Client ID ophalen via stats is niet mogelijk zonder bot online
        # Toon instructie
        self._toast("Gebruik /invite in Discord voor de link")

    def _toast(self, msg: str):
        """Tijdelijk statusbericht in de footer."""
        self.ftr_version_lbl.configure(text=msg, text_color=C_GREEN)
        self.after(3000, lambda: self.ftr_version_lbl.configure(
            text="CurseBot v2.0", text_color=C_MUTED
        ))

    def _on_close(self):
        """Bij sluiten: minimaliseer naar systeemvak ipv afsluiten."""
        self._hide_to_tray()

    def _hide_to_tray(self):
        """Verberg venster naar systeemvak."""
        self.withdraw()
        if not hasattr(self, "_tray_icon") or self._tray_icon is None:
            self._start_tray_icon()

    def _show_from_tray(self):
        """Herstel venster vanuit systeemvak."""
        self.deiconify()
        self.lift()
        self.focus_force()
        # Stop tray icon
        if hasattr(self, "_tray_icon") and self._tray_icon:
            try:
                self._tray_icon.stop()
            except Exception:
                pass
            self._tray_icon = None

    def _quit_from_tray(self):
        """Volledig afsluiten vanuit systeemvak."""
        if hasattr(self, "_tray_icon") and self._tray_icon:
            try:
                self._tray_icon.stop()
            except Exception:
                pass
            self._tray_icon = None
        self._poll_active = False
        # Stop bot indien draaiend
        if self._bot_manager and self._bot_manager.is_running:
            self._bot_manager.stop()
        self.after(500, self.destroy)

    def _start_tray_icon(self):
        """Start pystray icoon in achtergrondthread."""
        try:
            import pystray
            from PIL import Image

            # Logo laden voor tray (256x256 RGBA)
            _logo_path = BASE_DIR / "ui" / "assets" / "LOGOSMALL.png"
            if _logo_path.exists():
                tray_img = Image.open(_logo_path).convert("RGBA").resize(
                    (256, 256), Image.LANCZOS
                )
            else:
                # Fallback: eenvoudig goud vierkant
                tray_img = Image.new("RGBA", (64, 64), (245, 166, 35, 255))

            menu = pystray.Menu(
                pystray.MenuItem(
                    "⚡ CurseBot openen",
                    lambda icon, item: self.after(0, self._show_from_tray),
                    default=True  # dubbelklik activeert dit
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "▶ Bot starten" if not (self._bot_manager and self._bot_manager.is_running) else "⏹ Bot stoppen",
                    lambda icon, item: self.after(0,
                        self._do_start if not (self._bot_manager and self._bot_manager.is_running)
                        else self._do_stop
                    )
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "✕ Afsluiten",
                    lambda icon, item: self.after(0, self._quit_from_tray)
                ),
            )

            self._tray_icon = pystray.Icon(
                name="CurseBot",
                icon=tray_img,
                title="CurseBot — Slayer Alliance Edition",
                menu=menu,
            )

            # Draai in daemon thread zodat het de app niet blokkeert
            import threading
            t = threading.Thread(
                target=self._tray_icon.run,
                daemon=True, name="TrayThread"
            )
            t.start()

        except ImportError:
            # pystray niet geïnstalleerd — gewoon sluiten
            self._poll_active = False
            self.destroy()
        except Exception as e:
            # Tray niet beschikbaar (bijv. Linux zonder GTK) — gewoon sluiten
            self._poll_active = False
            self.destroy()

    def _on_unmap(self, event):
        """Gevangen bij minimize (iconify) → verstuur naar systeemvak."""
        if event.widget is self and self.state() == "iconic":
            self.after(50, self._hide_to_tray)

    def _check_setup(self):
        """Toon setup wizard als verplichte keys ontbreken."""
        try:
            from bot.services.key_manager import has_required_keys
            if not has_required_keys():
                self._open_setup_wizard()
        except ImportError:
            pass  # key_manager niet beschikbaar — geen wizard

    def _open_setup_wizard(self):
        """Open de setup wizard (modaal)."""
        try:
            from ui.setup_wizard import SetupWizard
            SetupWizard(self, on_complete=self._after_setup)
        except Exception as e:
            self._toast(f"⚠ Wizard fout: {e}")

    def _after_setup(self):
        """Callback na succesvolle setup wizard."""
        self._toast("✓ Configuratie opgeslagen — bot start op...")


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    app = CurseBotApp()
    app.mainloop()


if __name__ == "__main__":
    main()

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: ui/app.py │ v2.0.0 │ 2026-06-03                            ║
# ║  Native CustomTkinter UI — header/sidebar/grid/footer              ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
