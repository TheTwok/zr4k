import json
import urllib.parse
from fastapi import Header, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from aiogram.utils.web_app import check_webapp_signature
from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models import User

def verify_telegram_init_data(init_data: str, bot_token: str) -> dict | None:
    """
    Validates Telegram WebApp initData query string.
    Returns the parsed 'user' dictionary if signature matches, else None.
    Uses aiogram's official check_webapp_signature for robust verification.
    """
    if not check_webapp_signature(bot_token, init_data):
        return None
    try:
        params = dict(urllib.parse.parse_qsl(init_data))
        
        # Validate auth_date to prevent replay attacks
        auth_date = params.get("auth_date")
        if not auth_date:
            return None
        import time
        if time.time() - float(auth_date) > 86400: # 24 hours validity
            return None

        user_json = params.get("user")
        if user_json:
            return json.loads(user_json)
        return {}
    except Exception:
        return None

async def get_current_user(
    authorization: str = Header(None), 
    x_user_timezone: str = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    FastAPI dependency to authenticate and fetch the current user.
    Strictly verifies Telegram WebApp initData cryptographic signature.
    Allows local mock authentication only when settings.debug is True.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing."
        )

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "tma":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format. Use 'tma <initData>'."
        )

    init_data = parts[1]

    # Разрешаем mock-вход только в режиме отладки
    if settings.debug and init_data.startswith("mock_"):
        try:
            user_id = int(init_data.split("_")[1])
            username = f"mockuser_{user_id}"
            
            # Ищем или создаем пользователя в БД
            stmt = select(User).where(User.telegram_id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            # В режиме отладки только реальный ID админа
            is_admin_check = (user_id == settings.admin_user_id)
            
            if not user:
                user = User(
                    telegram_id=user_id,
                    username=username,
                    language_code="ru",
                    is_admin=is_admin_check,
                    timezone=x_user_timezone or "Europe/Moscow"
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
            else:
                updated = False
                if user.is_admin != is_admin_check:
                    user.is_admin = is_admin_check
                    updated = True
                if x_user_timezone and user.timezone != x_user_timezone:
                    user.timezone = x_user_timezone
                    updated = True
                if updated:
                    await db.commit()
            if user.is_banned:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ваш аккаунт заблокирован.")
            return user
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Mock login parsing failed: {str(e)}"
            )

    # Standard production Telegram initData validation (Strictly enforced)
    user_data = verify_telegram_init_data(init_data, settings.telegram_bot_token)
    if not user_data or "id" not in user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram initialization data signature."
        )

    user_id = user_data["id"]
    username = user_data.get("username")
    lang_code = user_data.get("language_code", "ru")
    is_admin_check = (user_id == settings.admin_user_id)

    stmt = select(User).where(User.telegram_id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            telegram_id=user_id,
            username=username,
            language_code=lang_code,
            is_admin=is_admin_check,
            timezone=x_user_timezone or "Europe/Moscow"
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        # Update details and admin status if changed
        updated = False
        if user.username != username:
            user.username = username
            updated = True
        if user.is_admin != is_admin_check:
            user.is_admin = is_admin_check
            updated = True
        if x_user_timezone and user.timezone != x_user_timezone:
            user.timezone = x_user_timezone
            updated = True
        if updated:
            await db.commit()

    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ваш аккаунт заблокирован."
        )

    return user

