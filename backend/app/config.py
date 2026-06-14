import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

LOCAL_HOSTS = ("localhost", "127.0.0.1", "0.0.0.0", "::1")

def get_env_int(key, default=0):
    val = os.getenv(key)
    if not val:
        return default
    try:
        val = val.strip("'\" ")
        return int(val)
    except ValueError:
        return default

def clean_env_value(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip("'\" \t\r\n")
    return value or None

def normalize_public_url(value: str | None) -> str | None:
    value = clean_env_value(value)
    if not value:
        return None
    if value.startswith(("http://", "https://")):
        return value.rstrip("/")
    return f"https://{value.rstrip('/')}"

def looks_like_public_host(value: str | None) -> bool:
    value = clean_env_value(value)
    if not value:
        return False
    host = value.replace("https://", "").replace("http://", "").split("/", 1)[0].split(":", 1)[0]
    if host in LOCAL_HOSTS:
        return False
    return "." in host

def get_fallback_app_url():
    url = normalize_public_url(os.getenv("APP_URL"))
    if url:
        return url
    
    for key in ("DOMAIN", "BOTHOST_DOMAIN", "PUBLIC_DOMAIN", "APP_DOMAIN", "APP_HOST", "WEBSITE_HOSTNAME"):
        domain = os.getenv(key)
        if looks_like_public_host(domain):
            return normalize_public_url(domain)
        
    return "http://localhost:8000"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="backend/.env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # JWT signing key for frontend token generation
    jwt_secret: str = Field(default="zr4k_secret_jwt_sign_key_928341")
    app_url: str = Field(default=get_fallback_app_url())
    debug: bool = Field(default=True)

    # DB & Redis URIs
    database_url: str = Field(default=os.getenv("DATABASE_URL", "sqlite+aiosqlite:////app/data/zr4k.db" if os.path.exists("/app/data") else "sqlite+aiosqlite:///zr4k.db"))
    redis_url: str = Field(default=os.getenv("REDIS_URL", "redis://localhost:6379/0"))

    # Client Bot token
    telegram_bot_token: str = Field(default=os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE"))

    # MTProto credentials
    telegram_api_id: int = Field(default=get_env_int("TELEGRAM_API_ID", 0))
    telegram_api_hash: str = Field(default=os.getenv("TELEGRAM_API_HASH", "YOUR_API_HASH_HERE"))

    # Groq, Mistral and Gemini keys
    groq_api_key: str = Field(default=os.getenv("GROQ_API_KEY", "YOUR_GROQ_API_KEY_HERE"))
    mistral_api_key: str = Field(default=os.getenv("MISTRAL_API_KEY", "YOUR_MISTRAL_API_KEY_HERE"))
    gemini_api_key: str = Field(default=os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE"))

    # Admin's Telegram ID to send alerts to
    admin_user_id: int = Field(default=get_env_int("ADMIN_USER_ID", 0))

settings = Settings()

# Prefer hosting-provided public domains over any APP_URL accidentally copied
# from a local tunnel .env file.
for domain_key in ("DOMAIN", "BOTHOST_DOMAIN", "PUBLIC_DOMAIN", "APP_DOMAIN", "APP_HOST", "WEBSITE_HOSTNAME"):
    domain = os.getenv(domain_key)
    if looks_like_public_host(domain):
        settings.app_url = normalize_public_url(domain)
        print(f"Public app URL from {domain_key}: {settings.app_url}")
        break
else:
    settings.app_url = normalize_public_url(settings.app_url) or "http://localhost:8000"

# Force persistent SQLite path inside /app/data on Bothost
if os.path.exists("/app/data"):
    if settings.database_url.startswith("sqlite"):
        settings.database_url = "sqlite+aiosqlite:////app/data/zr4k.db"

# Защита от кривого копирования: срезаем случайные кавычки и пробелы из URL
if settings.redis_url:
    settings.redis_url = settings.redis_url.strip("'\" ")

# Dynamic SQLite relative path resolver
if settings.database_url.startswith("sqlite"):
    url = settings.database_url
    if ":///" in url:
        scheme, path = url.split(":///", 1)
        if not path.startswith("/") and not (len(path) > 1 and path[1] == ":"):
            if path.startswith("app/data/") or path.startswith("data/"):
                settings.database_url = f"{scheme}:////app/data/" + path.split("data/", 1)[1]
            else:
                app_dir = os.path.dirname(os.path.abspath(__file__))
                backend_dir = os.path.dirname(app_dir)
                abs_path = os.path.abspath(os.path.join(backend_dir, path)).replace("\\", "/")
                settings.database_url = f"{scheme}:///{abs_path}"
