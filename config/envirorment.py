import os
import logging
from dotenv import load_dotenv

load_dotenv()


def load_env(key: str, default: str) -> str:
    """!
    os.getenv() wrapper that handles the case of None-types for not-set env-variables\n
    @param key: name of env variable to load
    @param default: default value if variable couldn't be loaded
    @return value of env variable or default value
    """
    value = os.getenv(key)
    if value:
        return value
    logger.warning(f"Can't load env-variable for: '{key}' - falling back to DEFAULT {key}='{default}'")
    return default


logger = logging.getLogger('bot')
SPOTIPY_ID = load_env("SPOTIPY_ID", 'unknown')
SPOTIPY_SECRET = load_env("SPOTIPY_SECRET", 'unknown')

TOKEN = load_env("TOKEN", 'unknown')
VERSION = load_env("VERSION", "unknown")
SERVER_INVITE = load_env("SERVER_INVITE", "unknown")
DEFAULT_PREFIX = load_env("DEFAULT_PREFIX", "!")
BOT = load_env("BOT", "unknown")
OWNER = load_env("OWNER", "unknown")

DATABASE_URL = load_env("DATABASE_URL", 'unknown')

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
