import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Add parent directory to path so app packages can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.config import settings

engine = create_async_engine(settings.database_url)

async def run():
    print(f"Connecting to database: {settings.database_url.split('@')[-1]}")
    async with engine.begin() as conn:
        # 1. Alter table user_channels
        try:
            await conn.execute(text('ALTER TABLE user_channels ADD COLUMN digest_schedule_time VARCHAR(5) NULL'))
            print("Migration: Added digest_schedule_time to user_channels successfully.")
        except Exception as e:
            print(f"Migration: digest_schedule_time on user_channels already exists or error: {e}")

        # 2. Create payments table
        try:
            await conn.execute(text('''
                CREATE TABLE IF NOT EXISTS payments (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
                    amount INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            '''))
            print("Migration: Created payments table successfully.")
        except Exception as e:
            print(f"Migration: Failed to create payments table: {e}")

        # 3. Create ai_usage_stats table
        try:
            await conn.execute(text('''
                CREATE TABLE IF NOT EXISTS ai_usage_stats (
                    id SERIAL PRIMARY KEY,
                    provider VARCHAR(50) NOT NULL,
                    prompt_tokens INTEGER DEFAULT 0,
                    completion_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    is_success BOOLEAN DEFAULT TRUE,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            '''))
            print("Migration: Created ai_usage_stats table successfully.")
        except Exception as e:
            print(f"Migration: Failed to create ai_usage_stats table: {e}")

    await engine.dispose()
    print("All migrations finished.")

if __name__ == "__main__":
    asyncio.run(run())
