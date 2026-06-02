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
import logging
import sys


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            "[%(asctime)s] [%(levelname)-8s] %(name)s — %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        logger.addHandler(handler)
    logger.propagate = False  # FIX: voorkom dubbele logging via root handler
    return logger


def configure_root_logger(level: str = "INFO") -> None:
    # Root logger alleen instellen voor libraries die geen eigen logger gebruiken
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            "[%(asctime)s] [%(levelname)-8s] %(name)s — %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        root.addHandler(handler)
    # discord.py en httpx eigen verbose logging dempen
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

# ╔══════════════════════════════════════════════════════════════════════╗
# ║                         FILE CARD                                    ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  File         : logger.py                                            ║
# ║  Role         : Util                                                 ║
# ║  Version      : 1.0.1                                                ║
# ║  Created      : 2026-06-02                                           ║
# ║  Last Updated : 2026-06-02  14:30                                    ║
# ║  Status       : Updated                                              ║
# ║  Notes        : Fix dubbele logging — propagate=False toegevoegd     ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  Created by Dieouwe                                                  ║
# ║  🌐 www.dieouwe.nl          ⚔️  www.slayeralliance.com              ║
# ║  📦 curseforge.com/members/dieouwe/projects                         ║
# ║  💬 discord.gg/y8Pu5qsEbQ                                           ║
# ╚══════════════════════════════════════════════════════════════════════╝
