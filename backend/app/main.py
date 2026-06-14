import json
import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from aiogram import Bot, types
from aiogram.types import WebAppInfo, MenuButtonWebApp, MenuButtonDefault

from backend.app.config import settings
from backend.app.database import engine, Base, get_db, ensure_db_exists, async_session
from backend.app.models import User, Channel, UserChannel, Keyword, CaughtMessage, Promocode, UserbotSession, Payment, AIUsageStat, DigestHistory
from backend.app.auth import get_current_user
import backend.app.crud as crud
import backend.app.schemas as schemas
from backend.app.digest import generate_summary
from backend.bot import dp, bot as client_bot
from backend.parser import start_parser, handle_control_action, fetch_history_direct
from backend.app.tasks import send_scheduled_digests, notify_users_expiry

logger = logging.getLogger("zr4k.main")
bot = client_bot

background_tasks = set()

async def scheduler_loop():
    logger.info("⏰ Starting internal scheduler loop...")
    # Wait a bit on startup
    await asyncio.sleep(10)
    while True:
        try:
            now = datetime.utcnow()
            # Run scheduled digests every hour (minute == 0)
            if now.minute == 0:
                logger.info("Scheduled time reached. Running send_scheduled_digests...")
                await send_scheduled_digests(None)
            
            # Run subscription check once a day at 10:00 UTC
            if now.hour == 10 and now.minute == 0:
                logger.info("PRO subscription check time reached. Running notify_users_expiry...")
                await notify_users_expiry(None)
                
        except Exception as e:
            logger.error(f"Error in scheduler loop: {e}")
        
        # Sleep until the start of the next minute
        now = datetime.utcnow()
        sleep_secs = 60 - now.second - (now.microsecond / 1000000.0)
        await asyncio.sleep(max(0.1, sleep_secs + 0.1))

async def start_client_bot():
    if client_bot is None:
        logger.error("🤖 Bot is not initialized (invalid token). Skipping client bot startup.")
        return
    try:
        # Delete webhook if set and start polling
        await client_bot.delete_webhook(drop_pending_updates=True)
        
        # Configure WebApp Menu Button
        app_url = settings.app_url
        is_https = app_url.startswith("https://")
        is_local = "localhost" in app_url or "127.0.0.1" in app_url
        
        if is_https and not is_local:
            try:
                await client_bot.set_chat_menu_button(
                    menu_button=MenuButtonWebApp(
                        text="Открыть",
                        web_app=WebAppInfo(url=app_url)
                    )
                )
                logger.info(f"Successfully configured Menu Button to WebApp: {app_url}")
            except Exception as e:
                logger.error(f"Failed to set WebApp Menu Button: {e}")
        else:
            try:
                await client_bot.set_chat_menu_button(
                    menu_button=MenuButtonDefault()
                )
                logger.info("Reset WebApp Menu Button to default (not HTTPS or local address).")
            except Exception as e:
                logger.error(f"Failed to reset WebApp Menu Button: {e}")

        await dp.start_polling(client_bot)
    except Exception as e:
        logger.error(f"Error starting client bot: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Гарантированно создаем папку для данных
    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    if "/" in db_path:
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
            
    # 2. Проверяем БД
    await ensure_db_exists()
    
    # 3. Создаем таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    # 4. Seed admin user
    if settings.admin_user_id:
        async with async_session() as session:
            stmt = select(User).where(User.telegram_id == settings.admin_user_id)
            res = await session.execute(stmt)
            admin_user = res.scalar_one_or_none()
            if not admin_user:
                admin_user = User(
                    telegram_id=settings.admin_user_id,
                    username="admin",
                    language_code="ru",
                    is_admin=True,
                    timezone="Europe/Moscow"
                )
                session.add(admin_user)
                await session.commit()
                logger.info(f"✅ Seeded admin user {settings.admin_user_id} automatically.")
    
    # 5. Start Bot, Parser, and Scheduler loop in background
    bot_task = asyncio.create_task(start_client_bot())
    parser_task = asyncio.create_task(start_parser())
    sched_task = asyncio.create_task(scheduler_loop())
    
    background_tasks.add(bot_task)
    background_tasks.add(parser_task)
    background_tasks.add(sched_task)
    
    yield
    
    # 6. Cleanups
    for task in background_tasks:
        task.cancel()
    await asyncio.gather(*background_tasks, return_exceptions=True)
    background_tasks.clear()
    if client_bot is not None:
        await client_bot.session.close()

app = FastAPI(title="ZR4K API", version="1.0.0", lifespan=lifespan)

# Enable CORS for frontend hosting
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "app_url": settings.app_url,
        "database": "sqlite" if settings.database_url.startswith("sqlite") else "postgres",
        "bot_configured": client_bot is not None,
        "frontend_dist": os.path.exists(frontend_dist),
    }

# ----------------- User & Settings Endpoints -----------------

@app.get("/api/user/me")
async def read_current_user(current_user: User = Depends(get_current_user)):
    return {
        "telegram_id": current_user.telegram_id,
        "username": current_user.username,
        "language_code": current_user.language_code,
        "is_pro": current_user.is_pro,
        "is_admin": current_user.is_admin,
        "pro_expires_at": current_user.pro_expires_at,
        "last_digest_at": current_user.last_digest_at,
        "digest_schedule_time": getattr(current_user, "digest_schedule_time", None)
    }

@app.post("/api/user/schedule")
async def update_digest_schedule(
    payload: schemas.ScheduleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.is_pro:
        raise HTTPException(status_code=403, detail="Расписание дайджеста доступно только на PRO-тарифе.")
    
    current_user.digest_schedule_time = payload.time # "HH:00" format or None
    await db.commit()
    return {"status": "success", "schedule": current_user.digest_schedule_time}

@app.post("/api/user/activate-promo", response_model=schemas.UserSchema)
async def activate_promo(
    payload: schemas.PromoCodeActivate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        updated_user = await crud.activate_promocode(db, current_user.telegram_id, payload.code)
        return updated_user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.post("/api/user/buy-pro")
async def buy_pro_subscription(
    current_user: User = Depends(get_current_user)
):
    """
    Triggers the Telegram Bot to send a Star Invoice directly in the user's private chat.
    """
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Бот временно недоступен."
        )
        
    try:
        await bot.send_invoice(
            chat_id=current_user.telegram_id,
            title="Подписка ZR4K PRO (30 дней)",
            description="Мониторинг до 100 источников, 200 фильтров и полный доступ к ИИ-дайджестам.",
            payload="pro_subscription_30",
            provider_token="", # Stars
            currency="XTR",
            prices=[types.LabeledPrice(label="ZR4K PRO - 30 дней", amount=50)],
            start_parameter="buy_pro_stars"
        )
        return {"status": "invoice_sent", "message": "Счет на оплату отправлен в личный диалог с ботом."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось отправить счет: {str(e)}"
        )

# ----------------- Sources Endpoints -----------------

@app.get("/api/sources", response_model=list[schemas.ChannelSchema])
async def get_sources(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await crud.get_channels_by_user(db, current_user.telegram_id)

@app.post("/api/sources", response_model=schemas.ChannelSchema)
async def add_source(
    payload: schemas.SourceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        channel, is_new_globally = await crud.add_user_channel(
            db, current_user.telegram_id, payload.link
        )
        
        # If the channel is brand new or needs to be monitored, instruct the parser bot
        if is_new_globally:
            await handle_control_action({
                "action": "join",
                "username": channel.username,
                "channel_id": channel.id
            })
            
        return channel
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.delete("/api/sources/{channel_id}")
async def remove_source(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Get channel info before deleting relation
    stmt = select(Channel).where(Channel.id == channel_id)
    res = await db.execute(stmt)
    channel = res.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Источник не найден.")

    should_leave = await crud.remove_user_channel(db, current_user.telegram_id, channel_id)
    
    # If no other user tracks this channel, instruct parser to leave
    if should_leave:
        await handle_control_action({
            "action": "leave",
            "username": channel.username,
            "channel_id": channel_id
        })
        
    return {"status": "success", "message": f"Канал '{channel.username}' успешно удален."}

@app.post("/api/sources/{channel_id}/schedule")
async def update_channel_schedule(
    channel_id: int,
    payload: schemas.ChannelScheduleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.is_pro:
        raise HTTPException(status_code=403, detail="Индивидуальное расписание рассылки доступно только на PRO-тарифе.")

    stmt = select(UserChannel).where(
        UserChannel.user_id == current_user.telegram_id,
        UserChannel.channel_id == channel_id,
        UserChannel.active == True
    )
    res = await db.execute(stmt)
    user_channel = res.scalar_one_or_none()
    if not user_channel:
        raise HTTPException(status_code=404, detail="Источник не найден.")

    user_channel.digest_schedule_time = payload.time
    user_channel.digest_schedule_days = payload.days
    await db.commit()
    return {
        "status": "success", 
        "digest_schedule_time": user_channel.digest_schedule_time,
        "digest_schedule_days": user_channel.digest_schedule_days
    }

# ----------------- Keywords/Filters Endpoints -----------------

@app.get("/api/sources/{channel_id}/keywords", response_model=list[schemas.KeywordSchema])
async def get_keywords(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify the user actually tracks this channel
    stmt = select(UserChannel).where(
        UserChannel.user_id == current_user.telegram_id,
        UserChannel.channel_id == channel_id,
        UserChannel.active == True
    )
    res = await db.execute(stmt)
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Вы не отслеживаете этот канал.")
        
    return await crud.get_keywords(db, current_user.telegram_id, channel_id)

@app.post("/api/sources/{channel_id}/keywords", response_model=schemas.KeywordSchema)
async def add_keyword(
    channel_id: int,
    payload: schemas.KeywordCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify the user tracks this channel
    stmt = select(UserChannel).where(
        UserChannel.user_id == current_user.telegram_id,
        UserChannel.channel_id == channel_id,
        UserChannel.active == True
    )
    res = await db.execute(stmt)
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Вы не отслеживаете этот канал.")

    try:
        kw = await crud.add_keyword(
            db, current_user.telegram_id, channel_id, payload.keyword, payload.mode
        )
        return kw
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.delete("/api/keywords/{keyword_id}")
async def remove_keyword(
    keyword_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    success = await crud.delete_keyword(db, current_user.telegram_id, keyword_id)
    if not success:
        raise HTTPException(status_code=400, detail="Ключевое слово не найдено или доступ запрещен.")
    return {"status": "success", "message": "Ключевое слово удалено."}

# ----------------- Caught Messages Endpoints -----------------

@app.get("/api/messages", response_model=list[schemas.CaughtMessageSchema])
async def get_messages(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(
            CaughtMessage.id,
            CaughtMessage.channel_id,
            Channel.username.label("channel_username"),
            Channel.title.label("channel_title"),
            CaughtMessage.message_id,
            CaughtMessage.text,
            CaughtMessage.url,
            CaughtMessage.created_at
        )
        .join(Channel, Channel.id == CaughtMessage.channel_id)
        .where(CaughtMessage.user_id == current_user.telegram_id)
        .order_by(CaughtMessage.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    res = await db.execute(stmt)
    
    # Map row result into schema dict
    messages = []
    for r in res.all():
        messages.append({
            "id": r.id,
            "channel_id": r.channel_id,
            "channel_username": r.channel_username,
            "channel_title": r.channel_title,
            "message_id": r.message_id,
            "text": r.text,
            "url": r.url,
            "created_at": r.created_at.isoformat() + "Z"
        })
    return messages

# ----------------- AI Digest Endpoint -----------------

@app.post("/api/digest")
async def generate_ai_digest(
    payload: schemas.DigestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Enforce PRO tariff restriction
    if not current_user.is_pro:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Генерация дайджестов доступна только пользователям PRO-тарифа."
        )

    # 2. Enforce 4-hour manual cooldown (Admins bypass this)
    now = datetime.utcnow()
    cooldown_hours = 4
    if current_user.last_digest_at and not current_user.is_admin:
        wait_time = current_user.last_digest_at + timedelta(hours=cooldown_hours) - now
        if wait_time > timedelta(0):
            minutes_left = int(wait_time.total_seconds() / 60)
            hours_left = minutes_left // 60
            mins_left = minutes_left % 60
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Генерировать дайджест можно не чаще одного раза в {cooldown_hours} часа. Пожалуйста, подождите {hours_left} ч. {mins_left} мин."
            )

    # 3. Retrieve channel usernames and session ids for user
    stmt = select(Channel).join(UserChannel, Channel.id == UserChannel.channel_id).where(UserChannel.user_id == current_user.telegram_id)
    if payload.channel_ids:
        stmt = stmt.where(Channel.id.in_(payload.channel_ids))
    res = await db.execute(stmt)
    channels = res.scalars().all()
    
    channels_data = [{"username": c.username, "session_id": c.userbot_session_id} for c in channels if c.userbot_session_id]
    
    if not channels_data:
        return {
            "status": "success",
            "digest": "Нет доступных источников для парсинга. Добавьте источники."
        }

    messages_texts = await fetch_history_direct(channels_data, payload.period_hours)

    if not messages_texts:
        return {
            "status": "success",
            "digest": "За указанный период сообщений в источниках не найдено, либо парсер не успел ответить за 30 секунд. Попробуйте еще раз."
        }

    # 4. Invoke LLM API
    digest_text = await generate_summary(messages_texts)



    # 5. Write last_digest_at and history in DB
    current_user.last_digest_at = now
    
    from backend.app.models import DigestHistory
    new_history = DigestHistory(
        user_id=current_user.telegram_id,
        text=digest_text,
        period_hours=payload.period_hours,
        created_at=now
    )
    db.add(new_history)
    await db.commit()

    return {
        "status": "success",
        "digest": digest_text
    }

@app.get("/api/digest/history")
async def get_digest_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from backend.app.models import DigestHistory
    stmt = select(DigestHistory).where(DigestHistory.user_id == current_user.telegram_id).order_by(DigestHistory.created_at.desc()).limit(20)
    res = await db.execute(stmt)
    history = res.scalars().all()
    return [{
        "id": h.id,
        "text": h.text,
        "period_hours": h.period_hours,
        "created_at": h.created_at.isoformat() + "Z"
    } for h in history]

@app.delete("/api/digest/history/{item_id}")
async def delete_digest_history_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from backend.app.models import DigestHistory
    stmt = select(DigestHistory).where(
        DigestHistory.id == item_id,
        DigestHistory.user_id == current_user.telegram_id
    )
    res = await db.execute(stmt)
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Запись не найдена.")
    await db.delete(item)
    await db.commit()
    return {"status": "success"}

# ----------------- Admin Endpoints -----------------

@app.post("/api/admin/create-promo", response_model=schemas.PromoCodeCreate)
async def admin_create_promo(
    payload: schemas.PromoCodeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.is_admin and current_user.telegram_id != settings.admin_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ ограничен. Только для администраторов."
        )
        
    try:
        promo = await crud.create_promocode(
            db, payload.code, payload.duration_days, payload.max_activations
        )
        return promo
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Не удалось создать промокод: {str(e)}")

@app.get("/api/admin/promocodes")
async def admin_get_promocodes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.is_admin and current_user.telegram_id != settings.admin_user_id:
        raise HTTPException(status_code=403, detail="Доступ ограничен.")
    stmt = select(Promocode)
    res = await db.execute(stmt)
    return res.scalars().all()

@app.delete("/api/admin/promocodes/{code}")
async def admin_delete_promocode(
    code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.is_admin and current_user.telegram_id != settings.admin_user_id:
        raise HTTPException(status_code=403, detail="Доступ ограничен.")
    from sqlalchemy import delete
    stmt = delete(Promocode).where(Promocode.code == code)
    res = await db.execute(stmt)
    await db.commit()
    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="Промокод не найден.")
    return {"status": "success", "message": "Промокод удален."}

@app.get("/api/admin/sessions")
async def admin_get_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.is_admin and current_user.telegram_id != settings.admin_user_id:
        raise HTTPException(status_code=403, detail="Доступ ограничен.")
    stmt = select(UserbotSession)
    res = await db.execute(stmt)
    return res.scalars().all()

@app.get("/api/admin/stats")
async def admin_get_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.is_admin and current_user.telegram_id != settings.admin_user_id:
        raise HTTPException(status_code=403, detail="Доступ ограничен.")
    
    total_users = await db.scalar(select(func.count(User.telegram_id)))
    now = datetime.utcnow()
    total_pro = await db.scalar(select(func.count(User.telegram_id)).where(User.pro_expires_at > now))
    total_channels = await db.scalar(select(func.count(Channel.id)))
    total_keywords = await db.scalar(select(func.count(Keyword.id)))
    total_messages = await db.scalar(select(func.count(CaughtMessage.id)))
    total_income = await db.scalar(select(func.sum(User.stars_income))) or 0
    
    # 1. Сбор детальной статистики ИИ (оптимизировано в 1 запрос)
    providers = ["groq", "gemini", "mistral"]
    ai_stats = {
        p: {
            "success_calls": 0,
            "failed_calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "today_success": 0,
            "today_failed": 0,
            "today_prompt": 0,
            "today_completion": 0,
            "today_total": 0
        }
        for p in providers
    }
    
    today_start = datetime.combine(now.date(), datetime.min.time())
    
    from sqlalchemy import case
    stmt_ai = select(
        AIUsageStat.provider,
        func.sum(case((AIUsageStat.is_success == True, 1), else_=0)).label("success_calls"),
        func.sum(case((AIUsageStat.is_success == False, 1), else_=0)).label("failed_calls"),
        func.sum(AIUsageStat.prompt_tokens).label("prompt_tokens"),
        func.sum(AIUsageStat.completion_tokens).label("completion_tokens"),
        func.sum(AIUsageStat.total_tokens).label("total_tokens"),
        func.sum(case(((AIUsageStat.is_success == True) & (AIUsageStat.created_at >= today_start), 1), else_=0)).label("today_success"),
        func.sum(case(((AIUsageStat.is_success == False) & (AIUsageStat.created_at >= today_start), 1), else_=0)).label("today_failed"),
        func.sum(case((AIUsageStat.created_at >= today_start, AIUsageStat.prompt_tokens), else_=0)).label("today_prompt"),
        func.sum(case((AIUsageStat.created_at >= today_start, AIUsageStat.completion_tokens), else_=0)).label("today_completion"),
        func.sum(case((AIUsageStat.created_at >= today_start, AIUsageStat.total_tokens), else_=0)).label("today_total")
    ).group_by(AIUsageStat.provider)
    
    res_ai = await db.execute(stmt_ai)
    for row in res_ai.all():
        p = row[0]
        if p in ai_stats:
            ai_stats[p] = {
                "success_calls": int(row[1] or 0),
                "failed_calls": int(row[2] or 0),
                "prompt_tokens": int(row[3] or 0),
                "completion_tokens": int(row[4] or 0),
                "total_tokens": int(row[5] or 0),
                "today_success": int(row[6] or 0),
                "today_failed": int(row[7] or 0),
                "today_prompt": int(row[8] or 0),
                "today_completion": int(row[9] or 0),
                "today_total": int(row[10] or 0)
            }

    # 2. График доходов за последние 7 дней (оптимизировано в 1 запрос)
    today = now.date()
    seven_days_ago = datetime.combine(today - timedelta(days=6), datetime.min.time())
    
    stmt_payments = select(Payment.amount, Payment.created_at).where(Payment.created_at >= seven_days_ago)
    res_payments = await db.execute(stmt_payments)
    payments = res_payments.all()
    
    income_by_date = {}
    for amount, created_at in payments:
        if created_at:
            date_str = created_at.date().isoformat()
            income_by_date[date_str] = income_by_date.get(date_str, 0) + amount
            
    income_chart_data = []
    for i in range(6, -1, -1):
        date_str = (today - timedelta(days=i)).isoformat()
        income_chart_data.append(income_by_date.get(date_str, 0))
        
    return {
        "total_users": total_users,
        "total_pro": total_pro,
        "total_channels": total_channels,
        "total_keywords": total_keywords,
        "total_messages": total_messages,
        "total_income": total_income,
        "ai_stats": ai_stats,
        "income_chart_data": income_chart_data
    }

@app.get("/api/admin/users")
async def admin_get_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.is_admin and current_user.telegram_id != settings.admin_user_id:
        raise HTTPException(status_code=403, detail="Доступ ограничен.")
    
    stmt = select(User).order_by(User.telegram_id.desc())
    res = await db.execute(stmt)
    users = res.scalars().all()
    
    return [
        {
            "telegram_id": u.telegram_id,
            "username": u.username,
            "is_pro": u.is_pro,
            "pro_expires_at": u.pro_expires_at,
            "is_banned": u.is_banned
        }
        for u in users
    ]

@app.get("/api/admin/users/{user_id}")
async def admin_get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403)
        
    stmt = select(User).where(User.telegram_id == user_id)
    res = await db.execute(stmt)
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
        
    # Get channels list
    stmt_chan = select(Channel.id, Channel.username, Channel.title).join(UserChannel, Channel.id == UserChannel.channel_id).where(UserChannel.user_id == user_id, UserChannel.active == True)
    res_chan = await db.execute(stmt_chan)
    user_channels = [{"id": row[0], "username": row[1], "title": row[2]} for row in res_chan.all()]

    
    # Get last 50 messages
    stmt_msg = (
        select(CaughtMessage.id, CaughtMessage.text, Channel.title, Channel.username, CaughtMessage.created_at, CaughtMessage.url)
        .join(Channel, CaughtMessage.channel_id == Channel.id)
        .where(CaughtMessage.user_id == user_id)
        .order_by(CaughtMessage.created_at.desc())
        .limit(50)
    )
    res_msg = await db.execute(stmt_msg)
    user_messages = [
        {
            "id": row[0], 
            "text": row[1], 
            "channel_title": row[2] or f"@{row[3]}", 
            "created_at": row[4].isoformat() + "Z",
            "url": row[5]
        } 
        for row in res_msg.all()
    ]
        
    return {
        "telegram_id": u.telegram_id,
        "username": u.username,
        "language_code": u.language_code,
        "is_pro": u.is_pro,
        "pro_expires_at": u.pro_expires_at.isoformat() + "Z" if u.pro_expires_at else None,
        "is_admin": u.is_admin,
        "is_banned": u.is_banned,
        "channels": user_channels,
        "messages": user_messages,
        "stats": {
            "channels": len(user_channels),
            "messages": len(user_messages)  # Last 50 shown but stats.messages could just be len for now
        }
    }

@app.post("/api/admin/users/{user_id}/ban")
async def admin_toggle_ban_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.is_admin and current_user.telegram_id != settings.admin_user_id:
        raise HTTPException(status_code=403, detail="Доступ ограничен.")
        
    if user_id == current_user.telegram_id:
        raise HTTPException(status_code=400, detail="Нельзя заблокировать самого себя.")
    
    stmt = select(User).where(User.telegram_id == user_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден.")
        
    user.is_banned = not user.is_banned
    await db.commit()
    
    return {"status": "success", "is_banned": user.is_banned}

from pydantic import BaseModel
class ManualProRequest(BaseModel):
    days: int

@app.post("/api/admin/users/{user_id}/pro")
async def admin_grant_pro(
    user_id: int,
    payload: ManualProRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.is_admin and current_user.telegram_id != settings.admin_user_id:
        raise HTTPException(status_code=403, detail="Доступ ограничен.")
        
    stmt = select(User).where(User.telegram_id == user_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден.")
        
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    
    if payload.days <= 0:
        user.pro_expires_at = None
    else:
        if user.pro_expires_at and user.pro_expires_at > now:
            user.pro_expires_at = user.pro_expires_at + timedelta(days=payload.days)
        else:
            user.pro_expires_at = now + timedelta(days=payload.days)
            
    await db.commit()
    return {"status": "success", "pro_expires_at": user.pro_expires_at.isoformat() + "Z" if user.pro_expires_at else None}

@app.post("/api/admin/users/{user_id}/reset-cooldown")
async def admin_reset_cooldown(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.is_admin and current_user.telegram_id != settings.admin_user_id:
        raise HTTPException(status_code=403, detail="Доступ ограничен.")
        
    stmt = select(User).where(User.telegram_id == user_id)
    res = await db.execute(stmt)
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="Пользователь не найден.")
        
    u.last_digest_at = None
    await db.commit()
    return {"status": "success"}



# Mount frontend build files
from fastapi.staticfiles import StaticFiles
import os

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
frontend_dist = os.path.join(base_dir, "frontend", "dist")

if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")
else:
    @app.get("/")
    async def root_fallback():
        return {"status": "running", "message": "ZR4K API is active. Frontend build not found, run 'npm run build' inside frontend folder."}

