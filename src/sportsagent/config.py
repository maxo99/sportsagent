import logging
import sys
from pathlib import Path

import dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

dotenv.load_dotenv()


class Settings(BaseSettings):
    # Project Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    SRC_DIR: Path = BASE_DIR / "src"
    DATA_DIR: Path = SRC_DIR / "data"
    LOG_LEVEL: str = "INFO"
    LLM_MODEL: str = "openai:gpt-4o"
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_API_KEY: str = ""
    ENABLE_CHECKPOINTING: bool = False
    DEFAULT_SESSION: str = "default_session"
    SAVE_HTML: bool = False
    SHOW_INTERNAL: bool = True
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()


def setup_logging(name: str | None = None) -> logging.Logger:
    logger = logging.getLogger(name if name else "sportsagent")

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        logger.setLevel(level)

    return logger
