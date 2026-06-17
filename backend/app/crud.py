from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, delete, update
from backend.app.models import User, Channel, UserChannel, Keyword, CaughtMessage, Promocode, Activation, UserbotSession

async def get_user(db: AsyncSession, user_id: int) -> User | None:
    stmt = select(User).where(User.telegram_id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, user_id: int, username: str | None = None, language_code: str = "ru") -> User:
    user = User(telegram_id=user_id, username=username, language_code=language_code)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def get_channels_by_user(db: AsyncSession, user_id: int) -> list[Channel]:
    stmt = (
        select(Channel, UserChannel.digest_schedule_time, UserChannel.digest_schedule_days)
        .join(UserChannel, UserChannel.channel_id == Channel.id)
        .where(UserChannel.user_id == user_id, UserChannel.active == True)
    )
    result = await db.execute(stmt)
    channels = []
    for channel, schedule_time, schedule_days in result.all():
        channel.digest_schedule_time = schedule_time
        channel.digest_schedule_days = schedule_days
        channels.append(channel)
    return channels

async def add_user_channel(db: AsyncSession, user_id: int, username: str) -> tuple[Channel, bool]:
    """
    Adds a channel for the user. Enforces Free/Pro source limits.
    Returns (Channel, is_new_globally).
    """
    user = await get_user(db, user_id)
    if not user:
        raise ValueError("User not found.")

    # 1. Enforce Source Limits
    user_channels = await get_channels_by_user(db, user_id)
    limit = 20 if user.is_pro else 1
    if len(user_channels) >= limit:
        if user.is_pro:
            raise ValueError("Достигнут максимум источников для PRO.")
        raise ValueError("Для добавления дополнительных источников нужна подписка PRO.")

    # 2. Get or create Channel
    stmt = select(Channel).where(Channel.username == username)
    result = await db.execute(stmt)
    channel = result.scalar_one_or_none()
    
    is_new_globally = False
    if not channel:
        channel = Channel(username=username)
        db.add(channel)
        await db.flush() # flush to get channel.id
        is_new_globally = True
    else:
        # Check if any user is currently monitoring this channel actively
        stmt_active = select(func.count(UserChannel.user_id)).where(
            UserChannel.channel_id == channel.id, 
            UserChannel.active == True
        )
        res_active = await db.execute(stmt_active)
        count_active = res_active.scalar() or 0
        if count_active == 0:
            is_new_globally = True

    # 3. Create mapping UserChannel
    stmt_mapping = select(UserChannel).where(
        UserChannel.user_id == user_id,
        UserChannel.channel_id == channel.id
    )
    res_mapping = await db.execute(stmt_mapping)
    mapping = res_mapping.scalar_one_or_none()
    
    if not mapping:
        mapping = UserChannel(user_id=user_id, channel_id=channel.id, active=True)
        db.add(mapping)
    elif not mapping.active:
        mapping.active = True
        
    await db.commit()
    channel.digest_schedule_time = None
    return channel, is_new_globally

async def remove_user_channel(db: AsyncSession, user_id: int, channel_id: int) -> bool:
    """
    Removes user's channel mapping.
    Returns should_leave (True if no other user monitors this channel).
    """
    stmt = select(UserChannel).where(
        UserChannel.user_id == user_id,
        UserChannel.channel_id == channel_id
    )
    result = await db.execute(stmt)
    mapping = result.scalar_one_or_none()
    
    if not mapping:
        return False
        
    mapping.active = False
    await db.flush()
    
    # Check if there are other active users tracking this channel
    stmt_other = select(func.count(UserChannel.user_id)).where(
        UserChannel.channel_id == channel_id,
        UserChannel.active == True
    )
    res_other = await db.execute(stmt_other)
    other_count = res_other.scalar() or 0
    
    should_leave = (other_count == 0)
    await db.commit()
    return should_leave

async def get_keywords(db: AsyncSession, user_id: int, channel_id: int) -> list[Keyword]:
    stmt = select(Keyword).where(Keyword.user_id == user_id, Keyword.channel_id == channel_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())

async def add_keyword(db: AsyncSession, user_id: int, channel_id: int, keyword: str, mode: str) -> Keyword:
    """
    Adds a keyword for a user-channel. Enforces Free/Pro keyword limits.
    """
    user = await get_user(db, user_id)
    if not user:
        raise ValueError("User not found.")
        
    # Check keyword count for this source
    stmt_count = select(func.count(Keyword.id)).where(
        Keyword.user_id == user_id,
        Keyword.channel_id == channel_id,
    )
    res_count = await db.execute(stmt_count)
    source_keywords = res_count.scalar() or 0
    
    limit = 20 if user.is_pro else 5
    if source_keywords >= limit:
        if user.is_pro:
            raise ValueError("Достигнут максимум ключевых слов для этого источника.")
        raise ValueError("Для добавления дополнительных ключевых слов нужна подписка PRO.")

    # Prevent duplicates
    stmt_dup = select(Keyword).where(
        Keyword.user_id == user_id,
        Keyword.channel_id == channel_id,
        Keyword.keyword == keyword,
        Keyword.mode == mode
    )
    res_dup = await db.execute(stmt_dup)
    existing = res_dup.scalar_one_or_none()
    if existing:
        return existing
        
    kw = Keyword(user_id=user_id, channel_id=channel_id, keyword=keyword, mode=mode)
    db.add(kw)
    await db.commit()
    await db.refresh(kw)
    return kw

async def delete_keyword(db: AsyncSession, user_id: int, keyword_id: int) -> bool:
    stmt = delete(Keyword).where(Keyword.id == keyword_id, Keyword.user_id == user_id)
    result = await db.execute(stmt)
    await db.commit()
    return (result.rowcount > 0)

async def save_caught_message(
    db: AsyncSession, 
    user_id: int, 
    channel_id: int, 
    message_id: int, 
    text: str, 
    url: str
) -> CaughtMessage:
    msg = CaughtMessage(
        user_id=user_id,
        channel_id=channel_id,
        message_id=message_id,
        text=text,
        url=url
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg

async def get_caught_messages(db: AsyncSession, user_id: int, limit: int = 50, offset: int = 0) -> list[CaughtMessage]:
    stmt = (
        select(CaughtMessage)
        .where(CaughtMessage.user_id == user_id)
        .order_by(CaughtMessage.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())

async def activate_promocode(db: AsyncSession, user_id: int, code: str) -> User:
    """
    Activates promocode for a user and extends PRO subscription.
    """
    # 1. Fetch promocode
    stmt_promo = select(Promocode).where(Promocode.code == code)
    res_promo = await db.execute(stmt_promo)
    promo = res_promo.scalar_one_or_none()
    
    if not promo:
        raise ValueError("Промокод не найден.")
        
    if promo.activations_count >= promo.max_activations:
        raise ValueError("Срок действия промокода истек (максимум активаций достигнут).")
        
    # 2. Check if user already activated this code
    stmt_act = select(Activation).where(Activation.user_id == user_id, Activation.code == code)
    res_act = await db.execute(stmt_act)
    existing_act = res_act.scalar_one_or_none()
    if existing_act:
        raise ValueError("Вы уже активировали этот промокод.")

    user = await get_user(db, user_id)
    if not user:
        raise ValueError("Пользователь не найден.")

    # 3. Update subscription duration
    now = datetime.utcnow()
    days = promo.duration_days
    
    if days >= 9999:
        # Lifetime
        user.pro_expires_at = now + timedelta(days=36500) # ~100 years
    else:
        if user.pro_expires_at and user.pro_expires_at > now:
            # Extend existing
            user.pro_expires_at = user.pro_expires_at + timedelta(days=days)
        else:
            # Set new expiration
            user.pro_expires_at = now + timedelta(days=days)

    # 4. Save Activation
    activation = Activation(user_id=user_id, code=code)
    db.add(activation)
    
    # 5. Update promocode activation count
    promo.activations_count += 1
    
    await db.commit()
    await db.refresh(user)
    return user

async def create_promocode(db: AsyncSession, code: str, duration_days: int, max_activations: int) -> Promocode:
    promo = Promocode(code=code, duration_days=duration_days, max_activations=max_activations)
    db.add(promo)
    await db.commit()
    await db.refresh(promo)
    return promo

async def get_active_userbot_sessions(db: AsyncSession) -> list[UserbotSession]:
    stmt = select(UserbotSession).where(UserbotSession.is_active == True)
    result = await db.execute(stmt)
    return list(result.scalars().all())

async def add_userbot_session(db: AsyncSession, phone: str, session_name: str) -> UserbotSession:
    stmt = select(UserbotSession).where(UserbotSession.phone == phone)
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    if not session:
        session = UserbotSession(phone=phone, session_name=session_name, is_active=True)
        db.add(session)
    else:
        session.is_active = True
    await db.commit()
    await db.refresh(session)
    return session

async def deactivate_userbot_session(db: AsyncSession, session_name: str):
    stmt = select(UserbotSession).where(UserbotSession.session_name == session_name)
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    if session:
        session.is_active = False
        await db.execute(update(Channel).where(Channel.userbot_session_id == session.id).values(userbot_session_id=None))
        await db.commit()
