import logging
import os
import sys
from pathlib import Path

import dotenv
import git
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

dotenv.load_dotenv()


# PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = Path(
    os.environ.get(
        "PROJECT_ROOT", str(git.Repo(".", search_parent_directories=True).working_tree_dir)
    ),
)


def default_asset_dir() -> Path:
    env_value = os.getenv("ASSET_OUTPUT_DIR")
    if env_value:
        return Path(env_value)
    return PROJECT_ROOT / "data" / "outputs"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    # Project Paths
    BASE_DIR: Path = PROJECT_ROOT
    SRC_DIR: Path = BASE_DIR / "src"
    DATA_DIR: Path = BASE_DIR / "data"
    # Logging and LLM Settings
    LOG_LEVEL: str = "INFO"
    LLM_MODEL: str = "openai:gpt-4o"
    OPENAI_MODEL: str = "gpt-4o"
    # API Keys and Feature Flags
    OPENAI_API_KEY: str = ""
    # SportsAgent Settings
    ENABLE_CHECKPOINTING: bool = False
    DEFAULT_SESSION: str = "default_session"
    SAVE_HTML: bool = False
    SHOW_INTERNAL: bool = True
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    AUTO_APPROVE_DEFAULT: bool = False
    SAVE_ASSETS_DEFAULT: bool = False
    ASSET_OUTPUT_DIR: Path = Field(default_factory=default_asset_dir)


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
