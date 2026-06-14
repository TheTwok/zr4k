import logging
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.future import select
from aiogram import Bot
from arq import cron
from arq.connections import RedisSettings
from backend.app.config import settings
from backend.app.database import async_session
from backend.app.models import User

logger = logging.getLogger("zr4k.tasks")

async def send_scheduled_digests(ctx):
    """
    Cron task running every hour. Finds user channel subscriptions with digest_schedule_time matching 
    the current hour in user's timezone and generates channel-specific digests for them.
    """
    logger.info("Starting scheduled digests task...")
    bot = Bot(token=settings.telegram_bot_token)
    now = datetime.utcnow()
    
    from zoneinfo import ZoneInfo
    from backend.app.models import CaughtMessage, Channel, UserChannel, DigestHistory
    from backend.app.digest import generate_summary
    from datetime import timezone
    
    async with async_session() as session:
        stmt = (
            select(UserChannel, Channel, User)
            .join(Channel, UserChannel.channel_id == Channel.id)
            .join(User, UserChannel.user_id == User.telegram_id)
            .where(
                UserChannel.active == True,
                UserChannel.digest_schedule_time.isnot(None),
                User.pro_expires_at > now
            )
        )
        res = await session.execute(stmt)
        rows = res.all()
        
    for user_channel, channel, user in rows:
        # Determine time in user's local timezone
        tz_str = user.timezone or "Europe/Moscow"
        try:
            user_tz = ZoneInfo(tz_str)
        except Exception:
            user_tz = ZoneInfo("Europe/Moscow")
            
        # Get user's current local time
        # now is UTC naive, let's localize it to UTC and then convert to user_tz
        utc_now = now.replace(tzinfo=timezone.utc)
        local_now = utc_now.astimezone(user_tz)
        
        local_hour_str = f"{local_now.hour:02d}:00"
        local_day_name = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"][local_now.weekday()]
        
        # Check if scheduled time matches the current local hour
        if user_channel.digest_schedule_time != local_hour_str:
            continue
            
        # Check if today is selected for newsletter
        days_str = user_channel.digest_schedule_days or "ПН,ВТ,СР,ЧТ,ПТ,СБ,ВС"
        enabled_days = [d.strip().upper() for d in days_str.split(",") if d.strip()]
        if local_day_name not in enabled_days:
            logger.info(f"Skipping scheduled digest for user {user.telegram_id} on channel {channel.username}: today {local_day_name} is not in {enabled_days}")
            continue

        try:
            async with async_session() as iteration_session:
                # Fetch 24 hours of messages strictly for this channel
                time_limit = now - timedelta(hours=24)
                msg_stmt = (
                    select(CaughtMessage.text)
                    .where(
                        CaughtMessage.user_id == user.telegram_id,
                        CaughtMessage.channel_id == channel.id,
                        CaughtMessage.created_at >= time_limit
                    )
                )
                msg_res = await iteration_session.execute(msg_stmt)
                msgs = msg_res.scalars().all()
                
                if msgs:
                    messages_texts = [
                        {"channel": channel.title or f"@{channel.username}", "text": m}
                        for m in msgs
                    ]
                    digest_text = await generate_summary(messages_texts, db=iteration_session)
                    
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=(
                            f"📰 **Ежедневный дайджест по каналу {channel.title or channel.username}**\n\n"
                            f"{digest_text}"
                        ),
                        parse_mode="Markdown"
                    )
                    
                    # Save to DigestHistory
                    history_item = DigestHistory(
                        user_id=user.telegram_id,
                        text=digest_text,
                        period_hours=24
                    )
                    iteration_session.add(history_item)
                    
                    # Update user last_digest_at
                    # Refresh/re-fetch user in iteration_session to avoid detached instance issues
                    user_stmt = select(User).where(User.telegram_id == user.telegram_id)
                    user_res = await iteration_session.execute(user_stmt)
                    db_user = user_res.scalar_one_or_none()
                    if db_user:
                        db_user.last_digest_at = now
                        
                    await iteration_session.commit()
                    logger.info(f"Sent and saved scheduled digest to user {user.telegram_id} for channel {channel.username}")
                else:
                    logger.info(f"No messages for scheduled channel {channel.username} and user {user.telegram_id}")
        except Exception as e:
            logger.error(f"Failed to send scheduled digest to {user.telegram_id} for channel {channel.username}: {e}")
                
    await bot.session.close()
    logger.info("Scheduled digests task completed.")

async def notify_users_expiry(ctx):
    """
    Cron task running daily to notify users whose PRO subscription is about to expire.
    Sends alerts at T-3 days and T-1 days.
    """
    logger.info("Starting PRO subscription expiration check...")
    
    bot = Bot(token=settings.telegram_bot_token)
    now = datetime.utcnow()
    
    # Target periods
    t_minus_3_start = now + timedelta(days=2)
    t_minus_3_end = now + timedelta(days=3)
    
    t_minus_1_start = now
    t_minus_1_end = now + timedelta(days=1)
    
    async with async_session() as session:
        # Check T-3 days
        stmt_3 = select(User).where(
            User.pro_expires_at >= t_minus_3_start,
            User.pro_expires_at <= t_minus_3_end
        )
        res_3 = await session.execute(stmt_3)
        users_3 = res_3.scalars().all()
        
        for user in users_3:
            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=(
                        "⚠️ Ваша подписка PRO истекает через 3 дня!\n\n"
                        "Продлите подписку в настройках Mini App, чтобы сохранить доступ к мониторингу до 100 каналов и ИИ-дайджестам."
                    )
                )
                logger.info(f"Sent T-3 warning to user {user.telegram_id}")
            except Exception as e:
                logger.error(f"Failed to send T-3 warning to user {user.telegram_id}: {str(e)}")
                
        # Check T-1 day
        stmt_1 = select(User).where(
            User.pro_expires_at >= t_minus_1_start,
            User.pro_expires_at <= t_minus_1_end
        )
        res_1 = await session.execute(stmt_1)
        users_1 = res_1.scalars().all()
        
        for user in users_1:
            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=(
                        "⚠️ Внимание! Ваша подписка PRO истекает менее чем через 24 часа!\n\n"
                        "Пожалуйста, продлите её в Mini App, чтобы избежать отключения отслеживания каналов."
                    )
                )
                logger.info(f"Sent T-1 warning to user {user.telegram_id}")
            except Exception as e:
                logger.error(f"Failed to send T-1 warning to user {user.telegram_id}: {str(e)}")
                
    await bot.session.close()
    logger.info("PRO subscription expiration check completed.")

# Arq worker settings
class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = None
    on_shutdown = None
    functions = [notify_users_expiry, send_scheduled_digests]
    
    # Run subscription check daily at 10:00 AM UTC
    cron_jobs = [
        cron(notify_users_expiry, hour=10, minute=0, unique=True),
        cron(send_scheduled_digests, minute=0, unique=True) # Run every hour
    ]
