import logging
import os
from pathlib import Path

from dotenv import load_dotenv


ENV_PATH = Path(__file__).with_name(".env")
load_dotenv(ENV_PATH)

logger = logging.getLogger("bot")


def load_env(key: str, default: str) -> str:
    value = os.getenv(key)
    if value:
        return value
    logger.warning("Can't load env-variable for: '%s' - falling back to DEFAULT %s='%s'", key, key, default)
    return default


def load_int_env(key: str, default: int) -> int:
    value = os.getenv(key)
    if value:
        try:
            return int(value)
        except ValueError:
            logger.warning("Can't parse env-variable '%s' as int - falling back to DEFAULT %s=%s", key, key, default)
    else:
        logger.warning("Can't load env-variable for: '%s' - falling back to DEFAULT %s=%s", key, key, default)
    return default


TOKEN = load_env("TOKEN", "unknown")
VERSION = load_env("VERSION", "unknown")
SERVER_INVITE = load_env("SERVER_INVITE", "unknown")
DEFAULT_PREFIX = load_env("DEFAULT_PREFIX", "!")
BOT = load_int_env("BOT", 0)
OWNER = load_int_env("OWNER", 0)

COLORS = {
    "WHITE": 0xFFFFFF,
    "AQUA": 0x1ABC9C,
    "GREEN": 0x2ECC71,
    "BLUE": 0x3498DB,
    "PURPLE": 0x9B59B6,
    "LUMINOUS_VIVID_PINK": 0xE91E63,
    "GOLD": 0xF1C40F,
    "ORANGE": 0xE67E22,
    "RED": 0xE74C3C,
    "NAVY": 0x34495E,
    "DARK_AQUA": 0x11806A,
    "DARK_GREEN": 0x1F8B4C,
    "DARK_BLUE": 0x206694,
    "DARK_PURPLE": 0x71368A,
    "DARK_VIVID_PINK": 0xAD1457,
    "DARK_GOLD": 0xC27C0E,
    "DARK_ORANGE": 0xA84300,
    "DARK_RED": 0x992D22,
    "DARK_NAVY": 0x2C3E50,
}
COLOR_LIST = [c for c in COLORS.values()]

PREFIX_LIST = ["!", "<", ">", "-", ".", "?", "$", "#"]
COG_HANDLER = ["load", "unload", "reload"]
