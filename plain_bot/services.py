from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from html import escape
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.types import User as TelegramUser
from sqlalchemy import and_, case, delete, func, or_, select, update

from backend.app import crud
from backend.app.config import settings
from backend.app.database import Base, async_session, engine, ensure_db_exists
from backend.app.digest import generate_summary
from backend.app.models import (
    AIUsageStat,
    BotText,
    CaughtMessage,
    Channel,
    Keyword,
    Payment,
    Promocode,
    User,
    UserChannel,
    UserbotSession,
)
from backend.parser import fetch_history_direct, handle_control_action


FREE_SOURCE_LIMIT = 1
FREE_KEYWORDS_PER_SOURCE = 5
PRO_SOURCE_LIMIT = 20
PRO_KEYWORDS_PER_SOURCE = 20
DIGEST_MAX_SOURCES = 5
DIGEST_MAX_MESSAGES_PER_SOURCE = 60
DIGEST_MAX_MESSAGE_CHARS = 700
DIGEST_MAX_PAYLOAD_CHARS = 14000
DIGEST_MAX_OUTPUT_CHARS = 3500


MODE_LABELS = {
    "semantic": "Смысловой",
    "exact": "Точный",
    "exact_phrase": "Точный",
    "exact_word": "Точный",
    "exclude": "Исключение",
}

DAY_PRESETS = {
    "all": ("Каждый день", "ПН,ВТ,СР,ЧТ,ПТ,СБ,ВС"),
    "work": ("Будни", "ПН,ВТ,СР,ЧТ,ПТ"),
    "weekend": ("Выходные", "СБ,ВС"),
}

TEXT_DEFAULTS = {
    "main": (
        "<b>ZR4K</b>\n"
        "Бот для мониторинга Telegram-каналов в реальном времени и умной ИИ-аналитики.\n\n"
        "<b>Что вы можете делать:</b>\n"
        "• Подключать Telegram-каналы как источники.\n"
        "• Настраивать смысловые, точные и исключающие фильтры.\n"
        "• Получать найденные совпадения прямо в чат.\n"
        "• Составлять ручные и автоматические AI-дайджесты.\n\n"
        "Выберите раздел ниже."
    ),
    "faq": (
        "<b>FAQ</b>\n"
        "Работа строится от источника к фильтрам.\n\n"
        "1. Добавьте публичный канал в разделе Источники.\n"
        "2. Добавьте фильтры для выбранного канала.\n"
        "3. Совпадения будут приходить сообщениями от бота и сохраняться в этом чате.\n"
        "4. В разделе AI Дайджест можно выбрать источник и составить AI-сводку или настроить ежедневную отправку.\n\n"
        "<b>Режимы фильтров</b>\n"
        "Смысловой: ищет сообщения по теме и близкому смыслу, даже если точной фразы нет в тексте.\n"
        "Точный: ищет указанное слово или фразу без смысловых расширений.\n"
        "Исключение: отсекает сообщения, где найдено указанное слово или фраза."
    ),
    "digest": (
        "<b>AI Дайджест</b>\n"
        "Выберите источник, затем укажите, когда хотите получать дайджест, или составьте его вручную."
    ),
}

TEXT_TITLES = {
    "main": "Основное приветствие",
    "faq": "FAQ",
    "digest": "AI Дайджест",
}


def clean_username(value: str) -> str:
    value = value.strip()
    if "/joinchat/" in value or "t.me/+" in value or "/+" in value or "joinchat" in value:
        raise ValueError("Поддерживаются только публичные каналы без invite-ссылок.")

    link_match = re.match(
        r"^(?:https?://)?(?:t\.me|telegram\.me|telegram\.dog)/?@?([a-zA-Z0-9_]{4,32})/?$",
        value,
        re.IGNORECASE,
    )
    if link_match:
        return link_match.group(1).lower()

    raw_match = re.match(r"^@?([a-zA-Z0-9_]{4,32})$", value)
    if raw_match:
        return raw_match.group(1).lower()

    raise ValueError("Неверный формат. Используйте @username или t.me/username.")


def error_text(exc: Exception) -> str:
    text = str(exc).strip()
    if not text:
        return "Операция не выполнена."
    if "Р" in text or "С" in text:
        return "Операция не выполнена. Проверьте данные или повторите позже."
    return text


def clip(text: str | None, limit: int = 900) -> str:
    if not text:
        return ""
    text = str(text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def dt_text(value: datetime | None) -> str:
    if not value:
        return "нет"
    return value.strftime("%d.%m.%Y %H:%M")


def is_owner_id(user_id: int | None) -> bool:
    return bool(settings.admin_user_id and user_id == settings.admin_user_id)


def is_owner(user: User | None) -> bool:
    return bool(user and is_owner_id(user.telegram_id))


def is_admin(user: User | None) -> bool:
    if not user:
        return False
    return is_owner(user)


def source_limit(user: User | None) -> int:
    return PRO_SOURCE_LIMIT if user and user.is_pro else FREE_SOURCE_LIMIT


def keyword_limit(user: User | None) -> int:
    return PRO_KEYWORDS_PER_SOURCE if user and user.is_pro else FREE_KEYWORDS_PER_SOURCE


def pro_until_text(user: User | None) -> str:
    if is_owner(user):
        return "Бессрочно"
    return dt_text(user.pro_expires_at if user else None)


def plan_label(user: User | None) -> str:
    return "PRO" if user and user.is_pro else "FREE"


def clip_digest(text: str) -> str:
    return clip(text, DIGEST_MAX_OUTPUT_CHARS)


def digest_to_html(text: str) -> str:
    escaped = escape(text)
    escaped = re.sub(r"^###\s*(.+)$", r"<b>\1</b>", escaped, flags=re.MULTILINE)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)


def prepare_digest_messages(messages_texts: list[dict | str]) -> list[dict | str]:
    grouped: dict[str, list[str]] = {}
    order: list[str] = []
    for item in messages_texts:
        if isinstance(item, dict):
            channel = str(item.get("channel") or "Неизвестный источник").strip()
            text = str(item.get("text") or "").strip()
        else:
            channel = "Неизвестный источник"
            text = str(item).strip()
        if not text:
            continue
        if channel not in grouped:
            grouped[channel] = []
            order.append(channel)
        if len(grouped[channel]) < DIGEST_MAX_MESSAGES_PER_SOURCE:
            grouped[channel].append(clip(text, DIGEST_MAX_MESSAGE_CHARS))

    prepared: list[dict[str, str]] = []
    total_chars = 0
    for channel in order[:DIGEST_MAX_SOURCES]:
        for text in grouped[channel]:
            if total_chars + len(text) > DIGEST_MAX_PAYLOAD_CHARS:
                return prepared
            prepared.append({"channel": channel, "text": text})
            total_chars += len(text)
    return prepared


async def init_storage() -> None:
    await ensure_db_exists()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    if settings.admin_user_id:
        async with async_session() as db:
            await db.execute(update(User).where(User.telegram_id != settings.admin_user_id).values(is_admin=False))
            stmt = select(User).where(User.telegram_id == settings.admin_user_id)
            res = await db.execute(stmt)
            admin = res.scalar_one_or_none()
            if not admin:
                admin = User(
                    telegram_id=settings.admin_user_id,
                    username="admin",
                    language_code="ru",
                    is_admin=True,
                    timezone="Europe/Moscow",
                )
                db.add(admin)
            else:
                admin.is_admin = True
                admin.is_banned = False
            await db.commit()


async def ensure_user(tg_user: TelegramUser) -> User:
    async with async_session() as db:
        user = await crud.get_user(db, tg_user.id)
        if not user:
            user = await crud.create_user(
                db,
                user_id=tg_user.id,
                username=tg_user.username,
                language_code=tg_user.language_code or "ru",
            )
        changed = False
        if user.username != tg_user.username:
            user.username = tg_user.username
            changed = True
        language_code = tg_user.language_code or user.language_code or "ru"
        if user.language_code != language_code:
            user.language_code = language_code
            changed = True
        if tg_user.id == settings.admin_user_id:
            if not user.is_admin:
                user.is_admin = True
                changed = True
            if user.is_banned:
                user.is_banned = False
                changed = True
        elif user.is_admin:
            user.is_admin = False
            changed = True
        if changed:
            await db.commit()
            await db.refresh(user)
        return user


async def get_user(user_id: int) -> User | None:
    async with async_session() as db:
        return await crud.get_user(db, user_id)


async def overview(user_id: int) -> dict:
    async with async_session() as db:
        user = await crud.get_user(db, user_id)
        sources_count = await db.scalar(
            select(func.count(UserChannel.channel_id)).where(
                UserChannel.user_id == user_id,
                UserChannel.active == True,
            )
        )
        keywords_count = await db.scalar(select(func.count(Keyword.id)).where(Keyword.user_id == user_id))
        source_rows = await db.execute(
            select(Channel.title, Channel.username, func.count(Keyword.id))
            .join(UserChannel, UserChannel.channel_id == Channel.id)
            .outerjoin(Keyword, and_(Keyword.channel_id == Channel.id, Keyword.user_id == user_id))
            .where(UserChannel.user_id == user_id, UserChannel.active == True)
            .group_by(Channel.id, Channel.title, Channel.username)
            .order_by(Channel.username.asc())
        )
        return {
            "user": user,
            "sources": sources_count or 0,
            "keywords": keywords_count or 0,
            "source_details": [
                {
                    "title": title or f"@{username}",
                    "username": username,
                    "keywords": count or 0,
                }
                for title, username, count in source_rows.all()
            ],
        }


async def get_bot_text(key: str) -> str:
    async with async_session() as db:
        item = await db.get(BotText, key)
        if item and item.text.strip():
            return item.text
    return TEXT_DEFAULTS.get(key, "")


async def set_bot_text(key: str, text: str) -> BotText:
    if key not in TEXT_DEFAULTS:
        raise ValueError("Неизвестный текст.")
    text = text.strip()
    if not text:
        raise ValueError("Текст не может быть пустым.")
    async with async_session() as db:
        item = await db.get(BotText, key)
        if not item:
            item = BotText(key=key, text=text)
            db.add(item)
        else:
            item.text = text
        await db.commit()
        await db.refresh(item)
        return item


async def list_sources(user_id: int) -> list[Channel]:
    async with async_session() as db:
        return await crud.get_channels_by_user(db, user_id)


async def list_digest_sources(user_id: int) -> list[Channel]:
    async with async_session() as db:
        stmt = (
            select(Channel)
            .join(UserChannel, UserChannel.channel_id == Channel.id)
            .where(
                UserChannel.user_id == user_id,
                UserChannel.active == True,
                Channel.userbot_session_id.isnot(None),
            )
            .order_by(Channel.username.asc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())


async def add_source(user_id: int, link: str) -> Channel:
    username = clean_username(link)
    async with async_session() as db:
        channel, is_new_globally = await crud.add_user_channel(db, user_id, username)
    if is_new_globally:
        await handle_control_action({"action": "join", "username": channel.username, "channel_id": channel.id})
    return channel


async def remove_source(user_id: int, channel_id: int) -> str:
    async with async_session() as db:
        stmt = select(Channel).where(Channel.id == channel_id)
        res = await db.execute(stmt)
        channel = res.scalar_one_or_none()
        if not channel:
            raise ValueError("Источник не найден.")
        username = channel.username
        should_leave = await crud.remove_user_channel(db, user_id, channel_id)
    if should_leave:
        await handle_control_action({"action": "leave", "username": username, "channel_id": channel_id})
    return username


async def list_keywords(user_id: int, channel_id: int) -> tuple[Channel, list[Keyword]]:
    async with async_session() as db:
        stmt = (
            select(Channel)
            .join(UserChannel, UserChannel.channel_id == Channel.id)
            .where(
                Channel.id == channel_id,
                UserChannel.user_id == user_id,
                UserChannel.active == True,
            )
        )
        res = await db.execute(stmt)
        channel = res.scalar_one_or_none()
        if not channel:
            raise ValueError("Источник не найден.")
        keywords = await crud.get_keywords(db, user_id, channel_id)
        return channel, keywords


async def add_keyword(user_id: int, channel_id: int, keyword: str, mode: str) -> Keyword:
    keyword = keyword.strip()
    if not keyword:
        raise ValueError("Введите непустое слово или фразу.")
    async with async_session() as db:
        stmt = select(UserChannel).where(
            UserChannel.user_id == user_id,
            UserChannel.channel_id == channel_id,
            UserChannel.active == True,
        )
        res = await db.execute(stmt)
        if not res.scalar_one_or_none():
            raise ValueError("Источник не найден.")
        return await crud.add_keyword(db, user_id, channel_id, keyword, mode)


async def delete_keyword(user_id: int, keyword_id: int) -> bool:
    async with async_session() as db:
        return await crud.delete_keyword(db, user_id, keyword_id)


async def generate_digest(user_id: int, period_hours: int, channel_ids: list[int] | None = None) -> str:
    selected_ids = [int(item) for item in (channel_ids or [])]
    if selected_ids and len(set(selected_ids)) > DIGEST_MAX_SOURCES:
        raise ValueError("Выбрано слишком много источников для одного AI Дайджеста.")

    async with async_session() as db:
        user = await crud.get_user(db, user_id)
        if not user or not user.is_pro:
            raise ValueError("AI Дайджест доступен только на PRO.")
        now = datetime.utcnow()
        if user.last_digest_at and not is_admin(user):
            wait_time = user.last_digest_at + timedelta(hours=4) - now
            if wait_time > timedelta(0):
                minutes_left = max(1, int(wait_time.total_seconds() / 60))
                raise ValueError(f"Следующий ручной AI Дайджест будет доступен через {minutes_left} мин.")

        stmt = (
            select(Channel)
            .join(UserChannel, Channel.id == UserChannel.channel_id)
            .where(
                UserChannel.user_id == user_id,
                UserChannel.active == True,
                Channel.userbot_session_id.isnot(None),
            )
            .order_by(Channel.username.asc())
        )
        if selected_ids:
            stmt = stmt.where(Channel.id.in_(set(selected_ids)))
        res = await db.execute(stmt)
        channels = res.scalars().all()
        channels_data = [{"username": c.username, "session_id": c.userbot_session_id} for c in channels[:DIGEST_MAX_SOURCES]]

    if not channels_data:
        return "Нет подключенных источников для парсинга."

    messages_texts = await fetch_history_direct(channels_data, period_hours)
    if not messages_texts:
        return "За выбранный период сообщений не найдено."

    prepared_messages = prepare_digest_messages(messages_texts)
    if not prepared_messages:
        return "За выбранный период не найдено подходящих текстовых сообщений."

    digest_text = clip_digest(await generate_summary(prepared_messages))

    async with async_session() as db:
        user = await crud.get_user(db, user_id)
        if user:
            user.last_digest_at = datetime.utcnow()
        await db.commit()

    return digest_text


async def set_schedule(user_id: int, channel_id: int, time_value: str | None, days: str | None = None) -> None:
    async with async_session() as db:
        stmt = select(UserChannel).where(
            UserChannel.user_id == user_id,
            UserChannel.channel_id == channel_id,
            UserChannel.active == True,
        )
        res = await db.execute(stmt)
        user_channel = res.scalar_one_or_none()
        if not user_channel:
            raise ValueError("Источник не найден.")
        user_channel.digest_schedule_time = time_value
        user_channel.digest_schedule_days = days
        await db.commit()


async def activate_promo(user_id: int, code: str) -> User:
    async with async_session() as db:
        return await crud.activate_promocode(db, user_id, code.strip())


async def save_payment(user_id: int, amount: int) -> None:
    async with async_session() as db:
        user = await crud.get_user(db, user_id)
        if not user:
            return
        now = datetime.utcnow()
        if user.pro_expires_at and user.pro_expires_at > now:
            user.pro_expires_at = user.pro_expires_at + timedelta(days=30)
        else:
            user.pro_expires_at = now + timedelta(days=30)
        user.stars_income = (user.stars_income or 0) + amount
        db.add(Payment(user_id=user_id, amount=amount))
        await db.commit()


async def scheduled_digest_tick(bot: Bot) -> None:
    now = datetime.utcnow()
    async with async_session() as session:
        stmt = (
            select(UserChannel, Channel, User)
            .join(Channel, UserChannel.channel_id == Channel.id)
            .join(User, UserChannel.user_id == User.telegram_id)
            .where(
                UserChannel.active == True,
                UserChannel.digest_schedule_time.isnot(None),
                or_(User.is_admin == True, User.pro_expires_at > now),
            )
        )
        res = await session.execute(stmt)
        rows = res.all()

    for user_channel, channel, user in rows:
        tz_str = user.timezone or "Europe/Moscow"
        try:
            user_tz = ZoneInfo(tz_str)
        except Exception:
            user_tz = ZoneInfo("Europe/Moscow")

        local_now = now.replace(tzinfo=timezone.utc).astimezone(user_tz)
        if user_channel.digest_schedule_time != f"{local_now.hour:02d}:{local_now.minute:02d}":
            continue

        local_day = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"][local_now.weekday()]
        enabled_days = [d.strip().upper() for d in (user_channel.digest_schedule_days or DAY_PRESETS["all"][1]).split(",")]
        if local_day not in enabled_days:
            continue

        try:
            async with async_session() as session:
                time_limit = now - timedelta(hours=24)
                msg_stmt = select(CaughtMessage.text).where(
                    CaughtMessage.user_id == user.telegram_id,
                    CaughtMessage.channel_id == channel.id,
                    CaughtMessage.created_at >= time_limit,
                )
                msg_res = await session.execute(msg_stmt)
                messages = msg_res.scalars().all()
                if not messages:
                    digest_text = "За последние 24 часа сообщений не найдено."
                    db_user = await crud.get_user(session, user.telegram_id)
                    if db_user:
                        db_user.last_digest_at = now
                    await session.commit()
                    await bot.send_message(
                        user.telegram_id,
                        f"<b>Ежедневный AI Дайджест</b>\n{escape(channel.title or '@' + channel.username)}\n\n{digest_text}",
                    )
                    continue
                messages_texts = prepare_digest_messages(
                    [{"channel": channel.title or f"@{channel.username}", "text": text} for text in messages]
                )
                if not messages_texts:
                    digest_text = "За последние 24 часа нет подходящих текстовых сообщений."
                    db_user = await crud.get_user(session, user.telegram_id)
                    if db_user:
                        db_user.last_digest_at = now
                    await session.commit()
                    await bot.send_message(
                        user.telegram_id,
                        f"<b>Ежедневный AI Дайджест</b>\n{escape(channel.title or '@' + channel.username)}\n\n{digest_text}",
                    )
                    continue
                digest_text = clip_digest(await generate_summary(messages_texts, db=session))
                db_user = await crud.get_user(session, user.telegram_id)
                if db_user:
                    db_user.last_digest_at = now
                await session.commit()
            await bot.send_message(
                user.telegram_id,
                f"<b>Ежедневный AI Дайджест</b>\n{escape(channel.title or '@' + channel.username)}\n\n{digest_to_html(digest_text)}",
            )
        except Exception:
            continue


async def expiry_tick(bot: Bot) -> None:
    now = datetime.utcnow()
    async with async_session() as session:
        stmt = select(User).where(
            User.is_admin == False,
            User.pro_expires_at >= now,
            User.pro_expires_at <= now + timedelta(days=1),
        )
        res = await session.execute(stmt)
        users = res.scalars().all()
    for user in users:
        try:
            await bot.send_message(
                user.telegram_id,
                "Подписка PRO истекает меньше чем через 24 часа. Продлите ее в разделе PRO.",
            )
        except Exception:
            continue


async def admin_stats() -> dict:
    async with async_session() as db:
        now = datetime.utcnow()
        pro_filter = or_(User.is_admin == True, User.pro_expires_at > now)
        free_filter = and_(User.is_admin == False, or_(User.pro_expires_at.is_(None), User.pro_expires_at <= now))
        provider_rows = await db.execute(
            select(
                AIUsageStat.provider,
                func.count(AIUsageStat.id),
                func.sum(case((AIUsageStat.is_success == True, 1), else_=0)),
                func.sum(case((AIUsageStat.is_success == False, 1), else_=0)),
                func.sum(AIUsageStat.total_tokens),
            )
            .group_by(AIUsageStat.provider)
        )
        ai_providers = {
            provider: {
                "calls": calls or 0,
                "success": success or 0,
                "failed": failed or 0,
                "tokens": tokens or 0,
            }
            for provider, calls, success, failed, tokens in provider_rows.all()
        }
        return {
            "users": await db.scalar(select(func.count(User.telegram_id))) or 0,
            "pro": await db.scalar(select(func.count(User.telegram_id)).where(pro_filter)) or 0,
            "free": await db.scalar(select(func.count(User.telegram_id)).where(free_filter)) or 0,
            "channels": await db.scalar(select(func.count(Channel.id))) or 0,
            "keywords": await db.scalar(select(func.count(Keyword.id))) or 0,
            "messages": await db.scalar(select(func.count(CaughtMessage.id))) or 0,
            "income": await db.scalar(select(func.sum(User.stars_income))) or 0,
            "ai_calls": await db.scalar(select(func.count(AIUsageStat.id))) or 0,
            "ai_providers": ai_providers,
        }


async def admin_users(segment: str, offset: int = 0, limit: int = 8) -> list[User]:
    async with async_session() as db:
        now = datetime.utcnow()
        stmt = select(User)
        if segment == "pro":
            stmt = stmt.where(or_(User.is_admin == True, User.pro_expires_at > now)).order_by(User.is_admin.desc(), User.telegram_id.desc())
        else:
            stmt = stmt.where(User.is_admin == False, or_(User.pro_expires_at.is_(None), User.pro_expires_at <= now)).order_by(User.telegram_id.desc())
        stmt = stmt.limit(limit).offset(offset)
        res = await db.execute(stmt)
        return list(res.scalars().all())


async def admin_user_details(user_id: int) -> tuple[User, int, int, int]:
    async with async_session() as db:
        user = await crud.get_user(db, user_id)
        if not user:
            raise ValueError("Пользователь не найден.")
        sources_count = await db.scalar(
            select(func.count(UserChannel.channel_id)).where(UserChannel.user_id == user_id, UserChannel.active == True)
        )
        keywords_count = await db.scalar(select(func.count(Keyword.id)).where(Keyword.user_id == user_id))
        messages_count = await db.scalar(select(func.count(CaughtMessage.id)).where(CaughtMessage.user_id == user_id))
        return user, sources_count or 0, keywords_count or 0, messages_count or 0


async def admin_toggle_ban(admin_id: int, target_id: int) -> bool:
    if admin_id == target_id or is_owner_id(target_id):
        raise ValueError("Владельца нельзя заблокировать.")
    async with async_session() as db:
        user = await crud.get_user(db, target_id)
        if not user:
            raise ValueError("Пользователь не найден.")
        user.is_banned = not user.is_banned
        await db.commit()
        return user.is_banned


async def admin_grant_pro(user_id: int, days: int) -> datetime | None:
    if is_owner_id(user_id):
        raise ValueError("У владельца бессрочный PRO по умолчанию.")
    async with async_session() as db:
        user = await crud.get_user(db, user_id)
        if not user:
            raise ValueError("Пользователь не найден.")
        now = datetime.utcnow()
        if days <= 0:
            user.pro_expires_at = None
        elif user.pro_expires_at and user.pro_expires_at > now:
            user.pro_expires_at += timedelta(days=days)
        else:
            user.pro_expires_at = now + timedelta(days=days)
        await db.commit()
        return user.pro_expires_at


async def admin_reset_cooldown(user_id: int) -> None:
    async with async_session() as db:
        user = await crud.get_user(db, user_id)
        if not user:
            raise ValueError("Пользователь не найден.")
        user.last_digest_at = None
        await db.commit()


async def admin_promos() -> list[Promocode]:
    async with async_session() as db:
        res = await db.execute(select(Promocode))
        return list(res.scalars().all())


async def admin_create_promo(code: str, days: int, uses: int) -> Promocode:
    async with async_session() as db:
        return await crud.create_promocode(db, code.strip(), days, uses)


async def admin_delete_promo(code: str) -> bool:
    async with async_session() as db:
        res = await db.execute(delete(Promocode).where(Promocode.code == code))
        await db.commit()
        return res.rowcount > 0


async def admin_sessions() -> list[UserbotSession]:
    async with async_session() as db:
        res = await db.execute(select(UserbotSession))
        return list(res.scalars().all())
