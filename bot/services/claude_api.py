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
import httpx
from bot.utils.logger import get_logger
from bot.utils.retry import async_retry

log = get_logger(__name__)

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL   = "claude-sonnet-4-20250514"


class ClaudeService:
    def __init__(self, api_key: str):
        self._headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    @async_retry(retries=2, delay=1.0)
    async def summarize_changelog(self, addon_name: str, changelog: str) -> str | None:
        """
        Vat een changelog samen in 3 bullet-points.
        Geeft None terug bij fout — caller valt dan terug op ruwe changelog.
        """
        if not changelog.strip():
            return None

        prompt = (
            f"Summarize the following WoW addon changelog for '{addon_name}' "
            f"in exactly 3 concise bullet points. English only. No preamble.\n\n"
            f"CHANGELOG:\n{changelog[:2000]}"
        )

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                r = await client.post(
                    CLAUDE_API_URL,
                    headers=self._headers,
                    json={
                        "model": CLAUDE_MODEL,
                        "max_tokens": 256,
                        "messages": [{"role": "user", "content": prompt}],
                    }
                )
                r.raise_for_status()
                content = r.json().get("content", [])
                for block in content:
                    if block.get("type") == "text":
                        return block["text"].strip()
        except Exception as exc:
            log.warning(f"[CLAUDE] Changelog samenvatting mislukt: {exc}")

        return None

# ╔══════════════════════════════════════════════════════════════════════╗
# ║                         FILE CARD                                    ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  File         : claude_api.py                                       ║
# ║  Role         : Core                                                ║
# ║  Version      : 1.0.0                                               ║
# ║  Created      : 2026-06-02                                          ║
# ║  Last Updated : 2026-06-02  13:45                                     ║
# ║  Status       : Updated                                             ║
# ║  Notes        : Optionele Claude API integratie (changelog samenvatting)║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  Created by Dieouwe                                                  ║
# ║  🌐 www.dieouwe.nl          ⚔️  www.slayeralliance.com              ║
# ║  📦 curseforge.com/members/dieouwe/projects                         ║
# ║  💬 discord.gg/y8Pu5qsEbQ                                           ║
# ╚══════════════════════════════════════════════════════════════════════╝
