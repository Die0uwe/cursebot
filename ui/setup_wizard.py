# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — ui/setup_wizard.py  v1.0.0

Setup wizard die verschijnt bij eerste start of als verplichte keys ontbreken.
Keys worden opgeslagen via key_manager (keyring / .env fallback).

Gebruik:
    from ui.setup_wizard import SetupWizard, needs_setup
    if needs_setup():
        wizard = SetupWizard(parent, on_complete=lambda: start_bot())
"""
import threading
import webbrowser
import customtkinter as ctk
from tkinter import messagebox

# Kleurenpalet — zelfde als ui/app.py
C_BG      = "#0b0d12"
C_BG2     = "#10131a"
C_BG3     = "#161922"
C_BORDER  = "#1e2235"
C_GOLD    = "#f5a623"
C_BLUE    = "#3d9eff"
C_GREEN   = "#2ecc71"
C_RED     = "#e74c3c"
C_PURPLE  = "#a78bfa"
C_TEXT    = "#cdd6f4"
C_MUTED   = "#6c7086"

FONT_TITLE = ("Segoe UI", 13, "bold")
FONT_BODY  = ("Segoe UI", 12)
FONT_SMALL = ("Segoe UI", 10)
FONT_MONO  = ("Consolas", 11)


def needs_setup() -> bool:
    """Geeft True als de setup wizard getoond moet worden."""
    try:
        from bot.services.key_manager import has_required_keys
        return not has_required_keys()
    except Exception:
        return False


class SetupWizard(ctk.CTkToplevel):
    """
    Eerste-start configuratievenster.
    Vraagt om verplichte keys, valideert ze, slaat ze op via keyring.

    Args:
        parent:      Tkinter parent widget (CurseBotApp)
        on_complete: Callback die aangeroepen wordt na succesvol opslaan
    """

    # (key_name, label, placeholder_hint, verplicht, toon_als_wachtwoord, help_url)
    FIELDS = [
        ("DISCORD_TOKEN",
         "Discord Bot Token",
         "Plak hier je bot token (van discord.com/developers)",
         True, True,
         "https://discord.com/developers/applications"),

        ("CURSEFORGE_API_KEY",
         "CurseForge API Key",
         "Plak hier je CF API key (van console.curseforge.com)",
         True, True,
         "https://console.curseforge.com/"),

        ("RELEASE_CHANNEL_ID",
         "Discord Channel ID",
         "Numeriek kanaal ID (bijv: 1234567890123456789)",
         True, False,
         "https://support.discord.com/hc/en-us/articles/206346498"),

        ("CF_AUTHOR_SLUG",
         "CurseForge gebruikersnaam",
         "Jouw CF gebruikersnaam (bijv: dieouwe)",
         False, False,
         None),

        ("CF_AUTHOR_ID",
         "CurseForge Auteur ID",
         "Numeriek auteur ID (bijv: 1417946)",
         False, False,
         None),
    ]

    def __init__(self, parent, on_complete):
        super().__init__(parent)
        self.title("CurseBot — Eerste configuratie")
        self.geometry("580x620")
        self.minsize(540, 560)
        self.resizable(True, False)
        self.configure(fg_color=C_BG)
        self.grab_set()           # modaal — blokkeert hoofdvenster
        self.lift()
        self.focus_force()

        self._on_complete = on_complete
        self._entries     = {}    # key_name → CTkEntry
        self._vars        = {}    # key_name → StringVar
        self._status_lbls = {}    # key_name → CTkLabel (validatiefeedback)
        self._saving      = False

        self._build()
        self._load_existing()     # vul al bekende waarden in (als update)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI Opbouw ──────────────────────────────────────────────────────────────

    def _build(self):
        # Header
        hdr = ctk.CTkFrame(self, fg_color=C_BG3, corner_radius=0,
                            border_width=1, border_color=C_BORDER, height=64)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text="⚡ CurseBot",
                     font=("Segoe UI", 15, "bold"),
                     text_color=C_GOLD).pack(side="left", padx=(16, 4), pady=16)
        ctk.CTkLabel(hdr, text="Eerste configuratie",
                     font=FONT_SMALL,
                     text_color=C_MUTED).pack(side="left", pady=16)

        # Scrollbaar formulier
        scroll = ctk.CTkScrollableFrame(self, fg_color=C_BG, corner_radius=0,
                                         scrollbar_button_color=C_BG3)
        scroll.pack(fill="both", expand=True)

        # Uitleg
        info = ctk.CTkFrame(scroll, fg_color=C_BG2, corner_radius=8,
                             border_width=1, border_color=C_BORDER)
        info.pack(fill="x", padx=16, pady=(16, 12))
        ctk.CTkLabel(info,
                     text="🔒  Keys worden versleuteld opgeslagen in Windows Credential Manager.\n"
                          "Ze worden nooit in plaintext bewaard of gelogd.",
                     font=FONT_SMALL, text_color=C_MUTED,
                     justify="left", wraplength=480).pack(padx=12, pady=10)

        # Formulier velden
        for key, label, hint, required, secret, help_url in self.FIELDS:
            self._build_field(scroll, key, label, hint, required, secret, help_url)

        # Opslaan knop
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(8, 4))

        self._save_btn = ctk.CTkButton(
            btn_frame, text="Opslaan & Starten",
            font=("Segoe UI", 12, "bold"),
            fg_color=C_GOLD, hover_color="#d4891e",
            text_color="#000000", height=42,
            command=self._on_save
        )
        self._save_btn.pack(fill="x")

        self._global_status = ctk.CTkLabel(
            scroll, text="",
            font=FONT_SMALL, text_color=C_RED, wraplength=520
        )
        self._global_status.pack(pady=(6, 16))

    def _build_field(self, parent, key, label, hint, required, secret, help_url):
        """Bouw één invoerveld met label, entry, validatiestatus en optionele help-link."""
        section = ctk.CTkFrame(parent, fg_color=C_BG2, corner_radius=8,
                                border_width=1, border_color=C_BORDER)
        section.pack(fill="x", padx=16, pady=4)

        # Label rij
        lbl_row = ctk.CTkFrame(section, fg_color="transparent")
        lbl_row.pack(fill="x", padx=12, pady=(10, 4))

        lbl_text = f"{label}{'  *' if required else '  (optioneel)'}"
        ctk.CTkLabel(lbl_row, text=lbl_text,
                     font=("Segoe UI", 11, "bold"),
                     text_color=C_TEXT if required else C_MUTED,
                     anchor="w").pack(side="left")

        if help_url:
            ctk.CTkButton(
                lbl_row, text="? Help",
                font=("Segoe UI", 9), width=52, height=20,
                fg_color="transparent", hover_color=C_BG3,
                border_color=C_BLUE, border_width=1,
                text_color=C_BLUE,
                command=lambda u=help_url: webbrowser.open(u)
            ).pack(side="right")

        # Entry rij
        entry_row = ctk.CTkFrame(section, fg_color="transparent")
        entry_row.pack(fill="x", padx=12, pady=(0, 4))

        var   = ctk.StringVar()
        entry = ctk.CTkEntry(
            entry_row,
            textvariable=var,
            placeholder_text=hint,
            show="•" if secret else "",
            font=FONT_MONO,
            fg_color=C_BG3,
            border_color=C_BORDER,
            text_color=C_TEXT,
            placeholder_text_color=C_MUTED,
            height=34
        )
        entry.pack(side="left", fill="x", expand=True)

        # Toon/verberg knop voor geheime velden
        if secret:
            self._build_toggle_btn(entry_row, entry)

        # Validatiestatus
        status_lbl = ctk.CTkLabel(
            section, text="",
            font=("Segoe UI", 10), text_color=C_RED, anchor="w"
        )
        status_lbl.pack(anchor="w", padx=12, pady=(0, 8))

        self._vars[key]        = var
        self._entries[key]     = entry
        self._status_lbls[key] = status_lbl

        # Live validatie bij focusverlies
        entry.bind("<FocusOut>", lambda e, k=key: self._validate_field(k))

    def _build_toggle_btn(self, parent, entry: ctk.CTkEntry):
        """Toon/verberg knop naast een wachtwoordveld."""
        showing = [False]

        def toggle():
            showing[0] = not showing[0]
            entry.configure(show="" if showing[0] else "•")
            btn.configure(text="●" if showing[0] else "○")

        btn = ctk.CTkButton(
            parent, text="○",
            font=("Segoe UI", 12), width=32, height=34,
            fg_color="transparent", hover_color=C_BG3,
            border_color=C_BORDER, border_width=1,
            text_color=C_MUTED,
            command=toggle
        )
        btn.pack(side="left", padx=(6, 0))

    # ── Logica ─────────────────────────────────────────────────────────────────

    def _load_existing(self):
        """Vul al bekende (niet-geheime) waarden in als dit een update is."""
        try:
            from bot.services.key_manager import get_key
            for key, _, _, _, secret, _ in self.FIELDS:
                if secret:
                    continue  # Toon bestaande tokens nooit
                val = get_key(key)
                if val:
                    self._vars[key].set(val)
        except Exception:
            pass

    def _validate_field(self, key: str) -> bool:
        """Valideer één veld en update het status-label. Geeft True terug bij succes."""
        try:
            from bot.services.key_manager import validate_key
        except ImportError:
            return True

        value    = self._vars[key].get().strip()
        required = next((req for k, _, _, req, _, _ in self.FIELDS if k == key), False)

        if not value:
            if required:
                self._set_field_status(key, "❌ Verplicht veld", C_RED)
                return False
            else:
                self._set_field_status(key, "", C_MUTED)
                return True

        ok, reason = validate_key(key, value)
        if ok:
            self._set_field_status(key, "✓ Geldig", C_GREEN)
            return True
        else:
            self._set_field_status(key, f"⚠ {reason}", C_GOLD)
            return True   # Waarschuwing, geen blokkade voor optionele keys

    def _set_field_status(self, key: str, text: str, color: str):
        if key in self._status_lbls:
            self._status_lbls[key].configure(text=text, text_color=color)

    def _on_save(self):
        if self._saving:
            return
        self._saving = True
        self._save_btn.configure(state="disabled", text="Opslaan...")
        self._global_status.configure(text="")

        # Valideer alle velden
        errors = []
        for key, label, _, required, _, _ in self.FIELDS:
            value = self._vars[key].get().strip()
            if required and not value:
                self._set_field_status(key, "❌ Verplicht veld", C_RED)
                errors.append(label)
            elif value:
                self._validate_field(key)

        if errors:
            self._global_status.configure(
                text=f"❌ Vul eerst in: {', '.join(errors)}"
            )
            self._save_btn.configure(state="normal", text="Opslaan & Starten")
            self._saving = False
            return

        # Sla op in achtergrond (keyring kan even duren)
        threading.Thread(target=self._save_worker, daemon=True).start()

    def _save_worker(self):
        """Achtergrondthread voor opslaan — UI-updates via self.after()."""
        try:
            from bot.services.key_manager import save_key
            saved = []
            for key, _, _, _, _, _ in self.FIELDS:
                value = self._vars[key].get().strip()
                if value:
                    save_key(key, value)
                    saved.append(key)

            self.after(0, lambda: self._on_save_done(saved))
        except Exception as e:
            self.after(0, lambda: self._on_save_error(str(e)))

    def _on_save_done(self, saved: list):
        self._global_status.configure(
            text=f"✓ {len(saved)} key(s) veilig opgeslagen", text_color=C_GREEN
        )
        self.after(800, self._complete)

    def _on_save_error(self, error: str):
        self._global_status.configure(
            text=f"❌ Fout bij opslaan: {error}", text_color=C_RED
        )
        self._save_btn.configure(state="normal", text="Opslaan & Starten")
        self._saving = False

    def _complete(self):
        self.grab_release()
        self.destroy()
        if self._on_complete:
            self._on_complete()

    def _on_close(self):
        if messagebox.askyesno(
            "Afsluiten",
            "Configuratie niet voltooid. CurseBot kan niet starten zonder keys.\nToch afsluiten?"
        ):
            self.grab_release()
            self.destroy()

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: setup_wizard.py │ v1.0.0 │ 2026-06-03                      ║
# ║  Role: Eerste-start configuratie UI — keyring integratie           ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
