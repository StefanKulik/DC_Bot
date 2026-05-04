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