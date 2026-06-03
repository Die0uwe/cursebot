# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — bot/i18n/translator.py  v1.0.0

Simpele i18n engine. Laadt strings.json, biedt t() functie voor vertalingen.
Fallback: NL → EN → sleutel zelf als alles ontbreekt.

Gebruik:
    from bot.i18n.translator import t, set_language, get_languages
    set_language("en")
    label = t("browser_title")           # → "CF Browser"
    msg   = t("wl_count", count=5)      # → "(5 addons)"
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from bot.utils.logger import get_logger

log = get_logger(__name__)

_STRINGS_PATH = Path(__file__).parent / "strings.json"
_strings:   dict = {}
_lang:      str  = "nl"
_fallback:  str  = "en"


def _load() -> None:
    """Laad strings.json eenmalig in geheugen."""
    global _strings
    if _strings:
        return
    try:
        with open(_STRINGS_PATH, encoding="utf-8") as f:
            _strings = json.load(f)
        log.info(f"[i18n] strings.json geladen — "
                 f"{len([k for k in _strings if not k.startswith('_')])} talen")
    except Exception as e:
        log.error(f"[i18n] strings.json laden mislukt: {e}")
        _strings = {}


def set_language(lang: str) -> bool:
    """
    Stel de actieve taal in.
    Geeft True terug als de taal beschikbaar is, anders False (taal ongewijzigd).
    """
    global _lang
    _load()
    if lang in _strings and not lang.startswith("_"):
        _lang = lang
        log.info(f"[i18n] Taal ingesteld: {lang}")
        return True
    log.warning(f"[i18n] Taal '{lang}' niet beschikbaar — blijft: {_lang}")
    return False


def get_language() -> str:
    """Geef de actieve taalcode terug."""
    return _lang


def get_languages() -> dict[str, str]:
    """
    Geef beschikbare talen terug als {code: naam} dict.
    Voorbeeld: {"nl": "Nederlands 🇳🇱", "en": "English 🇬🇧"}
    """
    _load()
    result = {}
    for code, data in _strings.items():
        if code.startswith("_") or not isinstance(data, dict):
            continue
        name  = data.get("_name", code)
        flag  = data.get("_flag", "")
        result[code] = f"{name} {flag}".strip()
    return result


def t(key: str, **kwargs) -> str:
    """
    Vertaal een sleutel naar de actieve taal.

    Fallback volgorde:
        1. Actieve taal
        2. Fallback taal (EN)
        3. Nederlands (NL)
        4. De sleutel zelf

    Variabelen:
        t("wl_count", count=5)  →  "(5 addons)"
    """
    _load()

    value = None

    # 1. Actieve taal
    lang_data = _strings.get(_lang, {})
    value = lang_data.get(key)

    # 2. Fallback taal
    if value is None and _lang != _fallback:
        fb_data = _strings.get(_fallback, {})
        value = fb_data.get(key)

    # 3. Nederlands
    if value is None and _lang != "nl":
        nl_data = _strings.get("nl", {})
        value = nl_data.get(key)

    # 4. Sleutel zelf
    if value is None:
        log.debug(f"[i18n] Sleutel niet gevonden: '{key}'")
        value = key

    # Variabelen invullen
    if kwargs:
        try:
            value = value.format(**kwargs)
        except (KeyError, ValueError) as e:
            log.debug(f"[i18n] Format fout voor '{key}': {e}")

    return value


def get_completion(lang: str) -> dict:
    """
    Geef de voltooiingsstatus van een taal terug.
    Handig voor de community editor.
    """
    _load()
    nl_keys = {k for k in _strings.get("nl", {}) if not k.startswith("_")}
    lang_keys = {k for k in _strings.get(lang, {}) if not k.startswith("_")}
    missing   = nl_keys - lang_keys
    pct       = int(len(lang_keys) / len(nl_keys) * 100) if nl_keys else 0
    return {
        "total":    len(nl_keys),
        "done":     len(lang_keys),
        "missing":  sorted(missing),
        "percent":  pct,
    }


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: translator.py │ v1.0.0 │ 2026-06-03                        ║
# ║  i18n engine — t(), set_language(), get_languages()                ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
