import sys
import asyncpg
from urllib.parse import urlparse
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from backend.app.config import settings

async def ensure_db_exists():
    """
    Проверяет существование целевой базы данных в PostgreSQL.
    Если её нет, создает её, подключаясь к дефолтной системной базе 'postgres'.
    """
    url = settings.database_url
    if "sqlite" in url or "supabase" in url:
        return
    parsed = urlparse(url)
    db_name = parsed.path.lstrip('/')
    
    # Формируем URL для подключения к системной базе postgres
    # Чтобы использовать стандартный коннектор asyncpg
    try:
        conn = await asyncpg.connect(
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            user=parsed.username or "postgres",
            password=parsed.password or "postgres",
            database="postgres"
        )
        try:
            exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db_name)
            if not exists:
                # В PostgreSQL создание базы нельзя запускать внутри транзакции
                await conn.execute(f'CREATE DATABASE "{db_name}"')
                print(f"✅ База данных '{db_name}' успешно создана.")
        finally:
            await conn.close()
    except Exception as e:
        print(f"⚠️ Предупреждение при проверке существования БД: {str(e)}")

# Create asynchronous engine
is_sqlite = settings.database_url.startswith("sqlite")
if is_sqlite:
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        future=True
    )
else:
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        future=True,
        pool_size=20,
        max_overflow=10
    )


# Async session factory
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

# Dependency injection for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
