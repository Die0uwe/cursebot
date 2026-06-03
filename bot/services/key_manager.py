# ==============================================================================
# Copyright (C) 2026  DieOuwe — GNU GPL v3
# ==============================================================================
"""
CurseBot — bot/services/key_manager.py  v1.0.0

Veilig beheer van API keys via OS-native keyring (Windows Credential Manager).
Volgorde bij ophalen: keyring → .env → os.environ
Volgorde bij opslaan: altijd naar keyring

Gebruik:
    from bot.services.key_manager import get_key, save_key, has_required_keys
"""
import os
import logging
from pathlib import Path

log = logging.getLogger(__name__)

APP_NAME = "CurseBot-SlayerAlliance"

# Keys die de bot nodig heeft
REQUIRED_KEYS = ["DISCORD_TOKEN", "CURSEFORGE_API_KEY", "RELEASE_CHANNEL_ID"]
OPTIONAL_KEYS = ["CF_AUTHOR_SLUG", "CF_AUTHOR_ID", "GUILD_ID",
                 "CHECK_INTERVAL_MINUTES", "LOG_LEVEL", "ANTHROPIC_API_KEY"]
ALL_KEYS      = REQUIRED_KEYS + OPTIONAL_KEYS

# Pad naar .env (naast de .exe of launch.py)
_ENV_PATH = Path(__file__).parent.parent.parent / ".env"

# ── Keyring backend laden (graceful fallback als niet geïnstalleerd) ──────────
try:
    import keyring
    import keyring.errors
    _KEYRING_OK = True
except ImportError:
    _KEYRING_OK = False
    log.warning("[KEY] keyring niet geïnstalleerd — val terug op .env. "
                "Installeer met: pip install keyring")


def _read_env() -> dict[str, str]:
    """Lees .env bestand als dict. Negeert comment-regels en lege regels."""
    result = {}
    if not _ENV_PATH.exists():
        return result
    try:
        for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip()
            # Sla placeholder-waarden over
            if v and not v.startswith("jouw_") and v != "":
                result[k] = v
    except Exception as e:
        log.debug(f"[KEY] .env lezen mislukt: {e}")
    return result


# ── Publieke API ───────────────────────────────────────────────────────────────

def get_key(name: str) -> str | None:
    """
    Haal key op in volgorde: keyring → .env → os.environ.
    Geeft None als nergens gevonden.
    """
    # 1. Keyring (versleuteld via OS)
    if _KEYRING_OK:
        try:
            val = keyring.get_password(APP_NAME, name)
            if val:
                return val
        except Exception as e:
            log.debug(f"[KEY] keyring.get_password mislukt voor {name}: {e}")

    # 2. .env bestand
    env = _read_env()
    if name in env:
        return env[name]

    # 3. OS omgevingsvariabele (server/CI/Railway/Render)
    return os.environ.get(name)


def save_key(name: str, value: str) -> bool:
    """
    Sla key op in keyring.
    Geeft True terug bij succes, False bij fout.
    """
    if not value or not value.strip():
        return False

    if _KEYRING_OK:
        try:
            keyring.set_password(APP_NAME, name, value.strip())
            log.info(f"[KEY] {name} opgeslagen in keyring")
            return True
        except Exception as e:
            log.error(f"[KEY] keyring.set_password mislukt voor {name}: {e}")

    # Fallback: schrijf naar .env als keyring niet werkt
    _write_to_env(name, value.strip())
    return False


def delete_key(name: str) -> bool:
    """Verwijder key uit keyring."""
    if not _KEYRING_OK:
        return False
    try:
        keyring.delete_password(APP_NAME, name)
        log.info(f"[KEY] {name} verwijderd uit keyring")
        return True
    except Exception:
        return False


def has_required_keys() -> bool:
    """Geeft True als alle verplichte keys beschikbaar zijn (niet leeg)."""
    return all(bool(get_key(k)) for k in REQUIRED_KEYS)


def get_missing_required() -> list[str]:
    """Geeft lijst van ontbrekende verplichte keys terug."""
    return [k for k in REQUIRED_KEYS if not get_key(k)]


def get_all_keys() -> dict[str, str | None]:
    """Haal alle bekende keys op als dict (voor Settings)."""
    return {k: get_key(k) for k in ALL_KEYS}


def migrate_from_env() -> list[str]:
    """
    Eenmalige migratie: verplaats .env keys naar keyring.
    Veilig om meerdere keren aan te roepen — slaat alleen over als al aanwezig.
    Geeft lijst van gemigreerde keys terug.
    """
    if not _KEYRING_OK:
        return []

    env        = _read_env()
    migrated   = []

    for key in ALL_KEYS:
        if key not in env:
            continue
        # Niet overschrijven als keyring al een waarde heeft
        try:
            existing = keyring.get_password(APP_NAME, key)
            if existing:
                continue
        except Exception:
            pass

        try:
            keyring.set_password(APP_NAME, key, env[key])
            migrated.append(key)
        except Exception as e:
            log.warning(f"[KEY] Migratie mislukt voor {key}: {e}")

    if migrated:
        log.info(f"[KEY] {len(migrated)} key(s) gemigreerd van .env naar keyring: {migrated}")

    return migrated


def _write_to_env(name: str, value: str):
    """Fallback: schrijf key naar .env als keyring niet beschikbaar is."""
    try:
        if _ENV_PATH.exists():
            lines = _ENV_PATH.read_text(encoding="utf-8").splitlines()
            updated = False
            for i, line in enumerate(lines):
                if "=" in line and not line.strip().startswith("#"):
                    k = line.split("=")[0].strip()
                    if k == name:
                        lines[i] = f"{name}={value}"
                        updated = True
                        break
            if not updated:
                lines.append(f"{name}={value}")
            _ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        else:
            _ENV_PATH.write_text(f"{name}={value}\n", encoding="utf-8")
        log.info(f"[KEY] {name} geschreven naar .env (keyring fallback)")
    except Exception as e:
        log.error(f"[KEY] .env schrijven mislukt voor {name}: {e}")


# ── Validatie ──────────────────────────────────────────────────────────────────

def validate_cf_key(key: str) -> bool:
    """CurseForge API keys zijn UUID-achtig: 36+ tekens met koppeltekens."""
    return bool(key) and len(key.strip()) >= 36 and "-" in key


def validate_discord_token(token: str) -> bool:
    """Discord bot tokens bestaan uit 3 delen gescheiden door punten."""
    return bool(token) and token.count(".") == 2 and len(token) >= 59


def validate_channel_id(cid: str) -> bool:
    """Discord snowflake IDs zijn 17–19 cijfers."""
    return cid.isdigit() and 17 <= len(cid) <= 19


VALIDATORS = {
    "DISCORD_TOKEN":      validate_discord_token,
    "CURSEFORGE_API_KEY": validate_cf_key,
    "RELEASE_CHANNEL_ID": validate_channel_id,
}


def validate_key(name: str, value: str) -> tuple[bool, str]:
    """
    Valideer een key-waarde.
    Geeft (True, "") bij succes, (False, "reden") bij fout.
    """
    if not value or not value.strip():
        return False, "mag niet leeg zijn"

    validator = VALIDATORS.get(name)
    if validator and not validator(value.strip()):
        hints = {
            "DISCORD_TOKEN":      "Token moet 3 delen hebben (punt-gescheiden) en 59+ tekens",
            "CURSEFORGE_API_KEY": "Key moet 36+ tekens zijn en koppeltekens bevatten",
            "RELEASE_CHANNEL_ID": "Channel ID moet 17–19 cijfers zijn",
        }
        return False, hints.get(name, "ongeldig formaat")

    return True, ""

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  File: key_manager.py │ v1.0.0 │ 2026-06-03                       ║
# ║  Role: API key beheer via keyring + .env fallback                  ║
# ║  Created by Dieouwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
# ╚══════════════════════════════════════════════════════════════════════╝
