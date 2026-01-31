import os
from pathlib import Path
from typing import Union
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).parent.parent.parent

class Settings(BaseSettings):
    # Server
    BACKEND_PORT: int = 8000
    SERVER_API_KEY: Union[str, None] = None
    API_VERSION: str = "v0"
    
    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4.1-mini"
    
    # Session Memory Settings
    TOKEN_THRESHOLD: int = 1000  # Trigger summarization when context exceeds this
    TIKTOKEN_MODEL: str = "o200k_base"  # Token counting model
    RECENT_MESSAGES_COUNT: int = 5  # Number of recent messages to keep for context
    
    # Memory Storage
    MEMORY_DIR: Path = ROOT_DIR / "backend" / "data" / "memory"
    
    # Constants
    ERROR_MESSAGE: str = "We are facing an issue, please try again later."

    model_config = SettingsConfigDict(
        env_file=[os.path.join(ROOT_DIR, ".env")],
        env_file_encoding='utf-8',
        extra='ignore'
    )

settings = Settings()

# Ensure memory directory exists
settings.MEMORY_DIR.mkdir(parents=True, exist_ok=True)

