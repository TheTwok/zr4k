import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def clean_env_value(value: str | None, default: str = "") -> str:
    if not value:
        return default
    value = value.strip("'\" \t\r\n")
    return value or default


def get_env_int(key: str, default: int = 0) -> int:
    value = clean_env_value(os.getenv(key))
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def default_database_url() -> str:
    if os.path.exists("/app/data"):
        return "sqlite+aiosqlite:////app/data/zr4k.db"
    return "sqlite+aiosqlite:///zr4k.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="backend/.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Kept for backward compatibility with existing local installs.
    jwt_secret: str = Field(default="zr4k_secret_jwt_sign_key_928341")
    debug: bool = Field(default=True)

    database_url: str = Field(default=clean_env_value(os.getenv("DATABASE_URL"), default_database_url()))

    telegram_bot_token: str = Field(default=clean_env_value(os.getenv("TELEGRAM_BOT_TOKEN"), "YOUR_BOT_TOKEN_HERE"))
    telegram_api_id: int = Field(default=get_env_int("TELEGRAM_API_ID", 0))
    telegram_api_hash: str = Field(default=clean_env_value(os.getenv("TELEGRAM_API_HASH"), "YOUR_API_HASH_HERE"))

    groq_api_key: str = Field(default=clean_env_value(os.getenv("GROQ_API_KEY"), "YOUR_GROQ_API_KEY_HERE"))
    mistral_api_key: str = Field(default=clean_env_value(os.getenv("MISTRAL_API_KEY"), "YOUR_MISTRAL_API_KEY_HERE"))
    gemini_api_key: str = Field(default=clean_env_value(os.getenv("GEMINI_API_KEY"), "YOUR_GEMINI_API_KEY_HERE"))

    admin_user_id: int = Field(default=get_env_int("ADMIN_USER_ID", 0))


settings = Settings()

if os.path.exists("/app/data") and settings.database_url.startswith("sqlite"):
    settings.database_url = "sqlite+aiosqlite:////app/data/zr4k.db"

if settings.database_url.startswith("sqlite") and ":///" in settings.database_url:
    scheme, path = settings.database_url.split(":///", 1)
    if not path.startswith("/") and not (len(path) > 1 and path[1] == ":"):
        app_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(app_dir)
        abs_path = os.path.abspath(os.path.join(backend_dir, path)).replace("\\", "/")
        settings.database_url = f"{scheme}:///{abs_path}"
