# ==============================================================================
# Copyright (C) 2026  DieOuwe (https://www.dieouwe.nl / https://www.slayeralliance.com)
#
# This work is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This work is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# ==============================================================================
import asyncio
import functools
from bot.utils.logger import get_logger

log = get_logger(__name__)


def async_retry(retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator: herprobeert een async functie bij uitzonderingen.
    Wacht na elke poging exponentieel langer (delay * backoff^poging).
    """
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(1, retries + 1):
                try:
                    return await fn(*args, **kwargs)
                except Exception as exc:
                    if attempt == retries:
                        log.error(f"[RETRY] {fn.__name__} definitief mislukt na {retries} pogingen: {exc}")
                        raise
                    log.warning(
                        f"[RETRY] {fn.__name__} poging {attempt}/{retries} mislukt: {exc}. "
                        f"Opnieuw in {current_delay:.1f}s"
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator

# ╔══════════════════════════════════════════════════════════════════════╗
# ║                         FILE CARD                                    ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  File         : retry.py                                            ║
# ║  Role         : Util                                                ║
# ║  Version      : 1.0.0                                               ║
# ║  Created      : 2026-06-02                                          ║
# ║  Last Updated : 2026-06-02  13:45                                     ║
# ║  Status       : Updated                                             ║
# ║  Notes        : Exponential backoff decorator voor async API calls  ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  Created by Dieouwe                                                  ║
# ║  🌐 www.dieouwe.nl          ⚔️  www.slayeralliance.com              ║
# ║  📦 curseforge.com/members/dieouwe/projects                         ║
# ║  💬 discord.gg/y8Pu5qsEbQ                                           ║
# ╚══════════════════════════════════════════════════════════════════════╝
