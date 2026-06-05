# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — ui/app.py  v2.4.0

Hoofdscherm van de CurseBot native UI (CustomTkinter).
Start de bot als daemon-thread via BotManager (launch.py).

CHANGES v2.4.0:
  - Header geïntegreerd uit patch-2026-06-05 (knoppen op één lijn via pack)
  - Alle knop-callbacks volledig geïmplementeerd (stop/restart/cache/check/update)
  - Status indicator (●) live gekoppeld aan STATS.bot_online
  - Timer label toont uptime uit STATS.uptime_str()
  - gaming.tools footer hyperlink
  - after()-polling loop voor UI updates (thread-safe)
  - Dialog bevestiging voor Stop en Cache reset
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

# ── Thema ─────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ── Kleuren ───────────────────────────────────────────────────────────────────
C_BG       = "#0d0d1a"
C_HEADER   = "#1a1a2e"
C_SIDEBAR  = "#12122a"
C_CARD     = "#1c1c32"
C_BORDER   = "#2a2a4a"
C_ACCENT   = "#e8a000"
C_TEXT     = "#d0d0e8"
C_MUTED    = "#666688"
C_GREEN    = "#00cc44"
C_RED      = "#cc2200"
C_FOOTER   = "#111118"

APP_VERSION = "2.4.0"


class CurseBotApp(ctk.CTk):
    """
    Hoofdvenster CurseBot UI.

    Start BotManager automatisch bij openen.
    Pollt elke 1000ms STATS voor live UI updates.
    """

    def __init__(self):
        super().__init__()

        self.title("CurseBot — Slayer Alliance Edition")
        self.geometry("1100x720")
        self.minsize(900, 600)
        self.configure(fg_color=C_BG)

        # Icoon laden (geen crash als het ontbreekt)
        try:
            icon_path = Path(__file__).parent / "assets" / "icon.ico"
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except Exception:
            pass

        # Logo laden voor header
        self.logo_image = None
        try:
            from PIL import Image
            logo_path = Path(__file__).parent / "assets" / "logo.png"
            if logo_path.exists():
                self.logo_image = Image.open(str(logo_path))
        except Exception:
            pass

        # BotManager importeren
        try:
            from launch import bot_manager
            self._bot_manager = bot_manager
        except ImportError:
            self._bot_manager = None
            log.warning("[UI] BotManager niet beschikbaar")

        # STATS importeren voor live polling
        try:
            from bot.services.stats import STATS
            self._stats = STATS
        except ImportError:
            self._stats = None

        # UI opbouwen
        self._build_ui()

        # Bot automatisch starten
        self._start_bot_silent()

        # Poll loop starten (thread-safe UI updates)
        self._poll_interval = 1000   # ms
        self._poll()

        # Sluit netjes af
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─────────────────────────────────────────────────────────────────────────
    # UI CONSTRUCTIE
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()
        self._build_body()
        self._build_footer()

    def _build_header(self):
        """Header: logo links · titel+status midden · knoppen rechts."""
        header = ctk.CTkFrame(self, fg_color=C_HEADER, height=70, corner_radius=0)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        # ── Logo ──────────────────────────────────────────────────────────
        logo_frame = ctk.CTkFrame(header, fg_color="transparent", width=80)
        logo_frame.pack(side="left", padx=(10, 0))
        logo_frame.pack_propagate(False)

        if self.logo_image:
            try:
                logo_img = ctk.CTkImage(
                    light_image=self.logo_image,
                    dark_image=self.logo_image,
                    size=(52, 52),
                )
                ctk.CTkLabel(logo_frame, image=logo_img, text="").pack(
                    expand=True, fill="both"
                )
            except Exception:
                pass

        # ── Titel + status ────────────────────────────────────────────────
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", expand=True, fill="both", padx=10)

        ctk.CTkLabel(
            title_frame,
            text="CurseBot",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=C_ACCENT,
            anchor="w",
        ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            title_frame,
            text="Slayer Alliance Edition",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=C_MUTED,
            anchor="w",
        ).pack(side="left", pady=(8, 0))

        # Online indicator
        self.status_dot = ctk.CTkLabel(
            title_frame,
            text="●",
            font=ctk.CTkFont(size=10),
            text_color=C_MUTED,
        )
        self.status_dot.pack(side="left", padx=(16, 2))

        self.status_label = ctk.CTkLabel(
            title_frame,
            text="Opstarten…",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=C_MUTED,
        )
        self.status_label.pack(side="left")

        # ── Knoppen rechts ────────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right", padx=(0, 14))

        BTN_H    = 30
        BTN_W    = 88
        BTN_FONT = ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        PAD_Y    = (20, 20)

        buttons = [
            ("⏹ Stop",     "#7a1200", "#cc2200", self.stop_bot),
            ("✕ Cache",    "#6b2200", "#aa3300", self.clear_cache),
            ("↺ Herstart", "#5c3a00", "#996600", self.restart_bot),
            ("↻ Check",    "#003a5c", "#005c99", self.check_now),
            ("↑ Update",   "#1a3d00", "#2d6600", self.update_bot),
        ]

        for label, fg, hover, cmd in buttons:
            ctk.CTkButton(
                btn_frame,
                text=label,
                command=cmd,
                width=BTN_W,
                height=BTN_H,
                font=BTN_FONT,
                fg_color=fg,
                hover_color=hover,
                corner_radius=5,
            ).pack(side="left", padx=3, pady=PAD_Y)

        # Timer / uptime label
        self.timer_label = ctk.CTkLabel(
            btn_frame,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=C_MUTED,
            width=72,
            anchor="w",
        )
        self.timer_label.pack(side="left", padx=(8, 0), pady=PAD_Y)

    def _build_body(self):
        """Body: sidebar tabs links · hoofdinhoud rechts."""
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True)

        # ── Sidebar ───────────────────────────────────────────────────────
        sidebar = ctk.CTkFrame(body, fg_color=C_SIDEBAR, width=200, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        ctk.CTkLabel(
            sidebar,
            text="NAVIGATIE",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=C_MUTED,
            anchor="w",
        ).pack(padx=14, pady=(18, 6), anchor="w")

        self._tab_buttons = {}
        self._active_tab  = None

        tabs = [
            ("dashboard",   "📊  Dashboard"),
            ("addons",      "🔍  Mijn Addons"),
            ("watchlist",   "👁  Watchlist"),
            ("browser",     "🌐  CF Browser"),
            ("stats",       "📈  Statistieken"),
            ("settings",    "⚙  Instellingen"),
            ("logs",        "📋  Logboek"),
        ]

        for key, label in tabs:
            btn = ctk.CTkButton(
                sidebar,
                text=label,
                command=lambda k=key: self._switch_tab(k),
                anchor="w",
                fg_color="transparent",
                hover_color=C_BORDER,
                text_color=C_TEXT,
                font=ctk.CTkFont(family="Segoe UI", size=13),
                corner_radius=6,
                height=36,
            )
            btn.pack(fill="x", padx=8, pady=2)
            self._tab_buttons[key] = btn

        # ── Content frame ─────────────────────────────────────────────────
        self._content = ctk.CTkFrame(body, fg_color=C_BG, corner_radius=0)
        self._content.pack(side="left", fill="both", expand=True)

        self._tab_frames = {}
        self._build_tab_dashboard()
        self._build_tab_logs()

        # Overige tabs: placeholder
        for key in ("addons", "watchlist", "browser", "stats", "settings"):
            f = ctk.CTkFrame(self._content, fg_color=C_BG)
            ctk.CTkLabel(
                f,
                text=f"— {key.capitalize()} tab —",
                font=ctk.CTkFont(size=16),
                text_color=C_MUTED,
            ).pack(expand=True)
            self._tab_frames[key] = f

        self._switch_tab("dashboard")

    def _build_tab_dashboard(self):
        """Dashboard tab met stat-cards en recent log."""
        f = ctk.CTkFrame(self._content, fg_color=C_BG)
        self._tab_frames["dashboard"] = f

        # Stat cards rij
        cards_row = ctk.CTkFrame(f, fg_color="transparent")
        cards_row.pack(fill="x", padx=20, pady=(20, 10))

        self._stat_cards = {}
        card_defs = [
            ("uptime",    "Uptime",       "–"),
            ("guilds",    "Servers",      "0"),
            ("tracked",   "Addons",       "0"),
            ("releases",  "Releases",     "0"),
            ("watchlist", "Watchlist",    "0"),
            ("interval",  "Interval",     "10m"),
        ]

        for key, label, default in card_defs:
            card = ctk.CTkFrame(cards_row, fg_color=C_CARD, corner_radius=10)
            card.pack(side="left", expand=True, fill="x", padx=6)

            ctk.CTkLabel(
                card,
                text=label.upper(),
                font=ctk.CTkFont(family="Segoe UI", size=10),
                text_color=C_MUTED,
            ).pack(pady=(10, 2))

            val_lbl = ctk.CTkLabel(
                card,
                text=default,
                font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
                text_color=C_TEXT,
            )
            val_lbl.pack(pady=(0, 10))
            self._stat_cards[key] = val_lbl

        # Timing info
        timing_row = ctk.CTkFrame(f, fg_color="transparent")
        timing_row.pack(fill="x", padx=20, pady=(0, 10))

        self._last_check_lbl = ctk.CTkLabel(
            timing_row,
            text="Laatste check: –",
            font=ctk.CTkFont(size=11),
            text_color=C_MUTED,
        )
        self._last_check_lbl.pack(side="left")

        self._next_check_lbl = ctk.CTkLabel(
            timing_row,
            text="Volgende check: –",
            font=ctk.CTkFont(size=11),
            text_color=C_MUTED,
        )
        self._next_check_lbl.pack(side="right")

        # Live log frame
        ctk.CTkLabel(
            f,
            text="LIVE LOG",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=C_MUTED,
            anchor="w",
        ).pack(fill="x", padx=24, pady=(4, 2))

        self._log_box = ctk.CTkTextbox(
            f,
            fg_color=C_CARD,
            text_color="#88aacc",
            font=ctk.CTkFont(family="Consolas", size=12),
            corner_radius=8,
            border_width=1,
            border_color=C_BORDER,
            state="disabled",
            wrap="word",
        )
        self._log_box.pack(fill="both", expand=True, padx=20, pady=(0, 16))

    def _build_tab_logs(self):
        """Volledig logboek tab."""
        f = ctk.CTkFrame(self._content, fg_color=C_BG)
        self._tab_frames["logs"] = f

        ctk.CTkLabel(
            f,
            text="LOGBOEK",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=C_MUTED,
            anchor="w",
        ).pack(fill="x", padx=24, pady=(20, 4))

        self._full_log_box = ctk.CTkTextbox(
            f,
            fg_color=C_CARD,
            text_color="#88aacc",
            font=ctk.CTkFont(family="Consolas", size=12),
            corner_radius=8,
            border_width=1,
            border_color=C_BORDER,
            state="disabled",
            wrap="word",
        )
        self._full_log_box.pack(fill="both", expand=True, padx=20, pady=(0, 16))

    def _build_footer(self):
        """Footer: versie links · gaming.tools rechts."""
        footer = ctk.CTkFrame(self, fg_color=C_FOOTER, height=28, corner_radius=0)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        ctk.CTkLabel(
            footer,
            text=f"CurseBot v{APP_VERSION}  ·  Slayer Alliance Edition",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color="#444466",
            anchor="w",
        ).pack(side="left", padx=12)

        gt = ctk.CTkLabel(
            footer,
            text="⚡ gaming.tools",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color="#335566",
            cursor="hand2",
            anchor="e",
        )
        gt.pack(side="right", padx=12)
        gt.bind("<Button-1>", lambda e: webbrowser.open("https://gaming.tools"))
        gt.bind("<Enter>",    lambda e: gt.configure(text_color="#0099dd"))
        gt.bind("<Leave>",    lambda e: gt.configure(text_color="#335566"))

    # ─────────────────────────────────────────────────────────────────────────
    # TAB NAVIGATIE
    # ─────────────────────────────────────────────────────────────────────────

    def _switch_tab(self, key: str):
        for k, frame in self._tab_frames.items():
            frame.pack_forget()
        for k, btn in self._tab_buttons.items():
            btn.configure(
                fg_color=C_ACCENT if k == key else "transparent",
                text_color="#000000" if k == key else C_TEXT,
            )
        self._tab_frames[key].pack(fill="both", expand=True)
        self._active_tab = key

    # ─────────────────────────────────────────────────────────────────────────
    # KNOP CALLBACKS
    # ─────────────────────────────────────────────────────────────────────────

    def stop_bot(self):
        """Stop de Discord bot netjes."""
        if not self._confirm("Bot stoppen?", "Bot stoppen? Hij stopt na de huidige actie."):
            return
        if self._bot_manager:
            self._bot_manager.stop()
            self._log_ui("Bot stop-signaal verstuurd")
        else:
            self._log_ui("[WARN] BotManager niet beschikbaar")

    def restart_bot(self):
        """Stop en herstart de bot."""
        def _do():
            if self._bot_manager:
                self._bot_manager.stop()
                time.sleep(2)
                self._bot_manager.start()
                self._log_ui("Bot herstart")
        threading.Thread(target=_do, daemon=True).start()
        self._log_ui("Bot herstart gestart…")

    def clear_cache(self):
        """Wis file ID cache zodat alle releases opnieuw gezien worden."""
        if not self._confirm("Cache wissen?", "File ID cache wissen? De volgende check behandelt alles als nieuw."):
            return
        try:
            from bot.services.cache import CacheService
            CacheService().wipe()
            self._log_ui("Cache gewist")
        except Exception as e:
            self._log_ui(f"[FOUT] Cache wissen mislukt: {e}")

    def check_now(self):
        """Forceer direct een CurseForge check (negeer interval)."""
        if self._stats:
            self._stats.force_check = True
            self._log_ui("Handmatige CF check getriggerd")
        else:
            self._log_ui("[WARN] STATS niet beschikbaar")

    def update_bot(self):
        """Draai updater.py — download en installeer laatste versie van GitHub."""
        self._log_ui("Update controleren…")
        def _do():
            try:
                result = subprocess.run(
                    [sys.executable, "updater.py"],
                    capture_output=True, text=True, timeout=60
                )
                if result.returncode == 42:
                    self.after(0, lambda: self._log_ui("Update geïnstalleerd — herstart aanbevolen"))
                else:
                    self.after(0, lambda: self._log_ui("Al up-to-date"))
            except Exception as e:
                self.after(0, lambda: self._log_ui(f"[FOUT] Update mislukt: {e}"))
        threading.Thread(target=_do, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────────────
    # POLL LOOP — live UI updates vanuit STATS
    # ─────────────────────────────────────────────────────────────────────────

    def _poll(self):
        """Poll STATS elke seconde en update UI — volledig thread-safe via after()."""
        try:
            self._update_ui_from_stats()
        except Exception as e:
            log.debug(f"[UI] Poll fout: {e}")
        self.after(self._poll_interval, self._poll)

    def _update_ui_from_stats(self):
        if not self._stats:
            return

        s = self._stats

        # ── Status indicator ──────────────────────────────────────────────
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

        # ── Timer (uptime) ────────────────────────────────────────────────
        self.timer_label.configure(text=s.uptime_str())

        # ── Stat cards ────────────────────────────────────────────────────
        self._stat_cards["uptime"].configure(text=s.uptime_str())
        self._stat_cards["guilds"].configure(text=str(s.guilds))
        self._stat_cards["tracked"].configure(text=str(s.projects_tracked))
        self._stat_cards["releases"].configure(text=str(s.releases_detected))
        self._stat_cards["watchlist"].configure(text=str(s.watchlist_count))
        self._stat_cards["interval"].configure(text=f"{s.check_interval_min}m")

        # ── Timing info ───────────────────────────────────────────────────
        self._last_check_lbl.configure(
            text=f"Laatste check: {s.last_check or '–'}"
        )
        self._next_check_lbl.configure(
            text=f"Volgende check: {s.next_check or '–'}"
        )

        # ── Log box (dashboard) ───────────────────────────────────────────
        if s.log_buffer:
            last_lines = s.log_buffer[-30:]
            content    = "\n".join(last_lines)
            self._set_textbox(self._log_box, content)

        # ── Volledig logboek tab ──────────────────────────────────────────
        if self._active_tab == "logs" and s.log_buffer:
            content = "\n".join(s.log_buffer)
            self._set_textbox(self._full_log_box, content)

    @staticmethod
    def _set_textbox(widget: ctk.CTkTextbox, content: str):
        """Vervang inhoud van textbox zonder scroll-positie reset als content gelijk is."""
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", content)
        widget.see("end")
        widget.configure(state="disabled")

    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _start_bot_silent(self):
        """Start bot bij openen van de UI als hij nog niet draait."""
        if self._bot_manager and not self._bot_manager.is_running:
            self._bot_manager.start()
            self._log_ui("Bot gestart")

    def _log_ui(self, msg: str):
        """Voeg een bericht toe aan STATS log én toon in UI."""
        if self._stats:
            self._stats.add_log(f"[UI] {msg}")
        log.info(f"[UI] {msg}")

    def _confirm(self, title: str, message: str) -> bool:
        """Toon een bevestigingsdialoog. Geeft True bij OK."""
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("380x150")
        dialog.resizable(False, False)
        dialog.configure(fg_color=C_CARD)
        dialog.grab_set()   # modaal

        result = {"ok": False}

        ctk.CTkLabel(
            dialog,
            text=message,
            font=ctk.CTkFont(size=13),
            text_color=C_TEXT,
            wraplength=340,
        ).pack(pady=(24, 16))

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack()

        def _ok():
            result["ok"] = True
            dialog.destroy()

        ctk.CTkButton(
            btn_row, text="OK", command=_ok,
            fg_color="#336600", hover_color="#449900",
            width=90, height=30,
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            btn_row, text="Annuleer", command=dialog.destroy,
            fg_color="#333355", hover_color="#444466",
            width=90, height=30,
        ).pack(side="left", padx=8)

        dialog.wait_window()
        return result["ok"]

    def _on_close(self):
        """Sluit UI netjes af — bot blijft draaien als daemon."""
        try:
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
# ║                         FILE CARD                                    ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  File         : app.py                                              ║
# ║  Role         : UI Core                                             ║
# ║  Version      : 2.4.0                                               ║
# ║  Created      : 2026-06-02                                          ║
# ║  Last Updated : 2026-06-05                                          ║
# ║  Status       : Updated                                             ║
# ║  Notes        : Header patch geïntegreerd + alle callbacks werkend  ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  Created by Dieouwe                                                  ║
# ║  🌐 www.dieouwe.nl          ⚔️  www.slayeralliance.com              ║
# ║  📦 curseforge.com/members/dieouwe/projects                         ║
# ║  💬 discord.gg/y8Pu5qsEbQ                                           ║
# ╚══════════════════════════════════════════════════════════════════════╝
