import os
import sqlite3

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
        db_path = find_sqlite_database("/app/data") or "/app/data/zr4k.db"
        return f"sqlite+aiosqlite:///{db_path}"
    return "sqlite+aiosqlite:///zr4k.db"


def score_sqlite_database(path: str) -> int:
    name = os.path.basename(path).lower()
    score = 0
    if name == "zr4k.db":
        score += 25
    if "zr4k" in name:
        score += 15
    try:
        if os.path.getsize(path) > 0:
            score += 10
    except OSError:
        return -1

    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            tables = {row[0] for row in conn.execute("select name from sqlite_master where type = 'table'")}
            score += len({"users", "channels", "user_channels", "keywords", "userbot_sessions"} & tables) * 20
            if "userbot_sessions" in tables:
                active_count = conn.execute("select count(*) from userbot_sessions where is_active = 1").fetchone()[0]
                score += min(int(active_count), 3) * 30
            if "users" in tables:
                users_count = conn.execute("select count(*) from users").fetchone()[0]
                score += min(int(users_count), 5) * 5
        finally:
            conn.close()
    except sqlite3.Error:
        pass
    return score


def find_sqlite_database(data_dir: str) -> str | None:
    try:
        entries = [os.path.join(data_dir, name) for name in os.listdir(data_dir)]
    except OSError:
        return None

    candidates = [
        path
        for path in entries
        if os.path.isfile(path)
        and os.path.splitext(path)[1].lower() in {".db", ".sqlite", ".sqlite3"}
        and not path.endswith(("-wal", "-shm", "-journal"))
    ]
    if not candidates:
        return None

    return max(candidates, key=score_sqlite_database)


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
    userbot_phone: str = Field(default=clean_env_value(os.getenv("USERBOT_PHONE"), ""))

    groq_api_key: str = Field(default=clean_env_value(os.getenv("GROQ_API_KEY"), "YOUR_GROQ_API_KEY_HERE"))
    mistral_api_key: str = Field(default=clean_env_value(os.getenv("MISTRAL_API_KEY"), "YOUR_MISTRAL_API_KEY_HERE"))
    gemini_api_key: str = Field(default=clean_env_value(os.getenv("GEMINI_API_KEY"), "YOUR_GEMINI_API_KEY_HERE"))

    admin_user_id: int = Field(default=get_env_int("ADMIN_USER_ID", 0))


settings = Settings()

if os.path.exists("/app/data") and settings.database_url.startswith("sqlite"):
    db_path = find_sqlite_database("/app/data") or "/app/data/zr4k.db"
    settings.database_url = f"sqlite+aiosqlite:///{db_path}"

if settings.database_url.startswith("sqlite") and ":///" in settings.database_url:
    scheme, path = settings.database_url.split(":///", 1)
    if not path.startswith("/") and not (len(path) > 1 and path[1] == ":"):
        app_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(app_dir)
        abs_path = os.path.abspath(os.path.join(backend_dir, path)).replace("\\", "/")
        settings.database_url = f"{scheme}:///{abs_path}"
