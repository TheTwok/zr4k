import logging
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, LabeledPrice, PreCheckoutQuery, Message, MenuButtonWebApp, MenuButtonDefault, MenuButtonCommands, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from sqlalchemy.future import select

# Add path so app packages can be imported
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.config import settings
from backend.app.database import async_session
from backend.app.models import User, Payment

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("zr4k.bot")

# Initialize Bot and Dispatcher safely
bot = None
token = settings.telegram_bot_token
if not token or token == "YOUR_BOT_TOKEN_HERE" or ":" not in token:
    logger.error("❌ TELEGRAM_BOT_TOKEN is missing or invalid! Bot features will be disabled.")
else:
    try:
        bot = Bot(token=token)
    except Exception as e:
        logger.error(f"❌ Failed to initialize Telegram Bot: {e}")

dp = Dispatcher()

# Price of PRO tariff in Telegram Stars (XTR)
PRO_PRICE_STARS = 50 # 50 Stars

@dp.message(CommandStart())
@dp.message(F.text.casefold() == "start")
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    lang = message.from_user.language_code or "ru"
    
    # 1. Register/fetch user in DB
    async with async_session() as db:
        stmt = select(User).where(User.telegram_id == user_id)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        
        if not user:
            user = User(
                telegram_id=user_id,
                username=username,
                language_code=lang
            )
            db.add(user)
            await db.commit()
            logger.info(f"Registered new user: {user_id}")
        else:
            if user.username != username:
                user.username = username
                await db.commit()

    # 2. Return welcome message with Inline WebApp Button "Открыть" immediately under it
    inline_keyboard = None
    app_url = settings.app_url
    is_https = app_url.startswith("https://")
    is_local = "localhost" in app_url or "127.0.0.1" in app_url
    
    if is_https and not is_local:
        inline_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Открыть", 
                        web_app=WebAppInfo(url=app_url)
                    )
                ]
            ]
        )
    
    warning_suffix = ""
    if not (is_https and not is_local):
        # For local development, send clickable link in the message text to avoid Telegram server-side block
        warning_suffix = (
            f"\n\n🔗 **[Открыть ZR4K в браузере (Локальный тест)]({app_url})**"
            f"\n\n⚠️ **Заметка разработчика:** Ссылки на `localhost` или `http` заблокированы серверами Telegram для использования в инлайн-кнопках. "
            "Поэтому для локального тестирования мы вывели кликабельную ссылку текстом выше. "
            "Для полноценного Mini App внутри Telegram укажите публичный HTTPS-адрес (например, через `ngrok`) в `.env`."
        )
    
    welcome_text = (
        f"Привет, {first_name}! 👋\n\n"
        f"**ZR4K** — это инновационное приложение для мониторинга Telegram-каналов в реальном времени и умной ИИ-аналитики.\n\n"
        f"🔥 **Что вы можете делать:**\n"
        f"• Добавлять каналы-источники\n"
        f"• Настраивать умные фильтры ключевых слов (семантический поиск, исключения, точные фразы)\n"
        f"• Получать мгновенные уведомления о совпадениях\n"
        f"• Генерировать краткие ИИ-дайджесты новостей за выбранный период!{warning_suffix}"
    )
    
    await message.answer(welcome_text, reply_markup=inline_keyboard, parse_mode="Markdown", disable_web_page_preview=True)
    


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "📖 **Справка по боту ZR4K**:\n\n"
        "1. Чтобы начать работу, откройте Mini App по кнопке в приветственном сообщении или введите /start.\n"
        "2. Вы можете активировать PRO-подписку прямо в приложении (вкладка Настройки) или отправив запрос боту.\n"
        "3. Наш парсер отслеживает сообщения в реальном времени, проверяет ключевые слова и присылает алерты сюда.\n\n"
        "Для покупки PRO-подписки напрямую через Stars введите /buy_pro."
    )
    await message.answer(help_text, parse_mode="Markdown")

@dp.message(Command("buy_pro"))
async def cmd_buy_pro(message: Message):
    """
    Sends an invoice for the PRO subscription using Telegram Stars (XTR).
    """
    user_id = message.from_user.id
    
    # Send invoice
    await bot.send_invoice(
        chat_id=user_id,
        title="Подписка ZR4K PRO (30 дней)",
        description="Мониторинг до 100 каналов, 200 фильтров и полный доступ к ИИ-дайджестам новостей.",
        payload="pro_subscription_30",
        provider_token="", # Empty for Telegram Stars
        currency="XTR",
        prices=[
            LabeledPrice(label="ZR4K PRO - 30 дней", amount=PRO_PRICE_STARS)
        ],
        start_parameter="buy_pro_stars"
    )

@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    """
    Verifies that the payment can proceed.
    """
    # Verify payload
    if pre_checkout_query.invoice_payload == "pro_subscription_30":
        await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
    else:
        await bot.answer_pre_checkout_query(
            pre_checkout_query.id, 
            ok=False, 
            error_message="Произошла ошибка при валидации заказа."
        )

@dp.message(F.successful_payment)
async def process_successful_payment(message: Message):
    """
    Processes a successful Stars payment and extends the user's PRO subscription.
    """
    payment_info = message.successful_payment
    user_id = message.from_user.id
    
    if payment_info.invoice_payload == "pro_subscription_30":
        async with async_session() as db:
            stmt = select(User).where(User.telegram_id == user_id)
            res = await db.execute(stmt)
            user = res.scalar_one_or_none()
            
            if user:
                now = datetime.utcnow()
                if user.pro_expires_at and user.pro_expires_at > now:
                    # Extend existing
                    user.pro_expires_at = user.pro_expires_at + timedelta(days=30)
                else:
                    # Set new expiration date
                    user.pro_expires_at = now + timedelta(days=30)
                    
                user.stars_income = (user.stars_income or 0) + payment_info.total_amount
                payment = Payment(user_id=user_id, amount=payment_info.total_amount)
                db.add(payment)
                await db.commit()
                logger.info(f"User {user_id} upgraded to PRO via Stars payment. Transaction logged.")
                
                await message.answer(
                    "🎉 **Спасибо за покупку!**\n\n"
                    "Ваша подписка **ZR4K PRO** успешно активирована на 30 дней.\n"
                    "Теперь вам доступны расширенные лимиты на каналы, фильтры и генерация ИИ-дайджестов!",
                    parse_mode="Markdown"
                )
            else:
                await message.answer("Ошибка: Пользователь не найден в базе данных. Пожалуйста, введите /start.")

async def main():
    logger.info("Starting ZR4K Client Bot...")
    if bot is None:
        logger.error("❌ Bot is not initialized (invalid token). Cannot run main polling loop.")
        return
    # Delete webhook if set and start polling
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Configure WebApp Menu Button
    app_url = settings.app_url
    is_https = app_url.startswith("https://")
    is_local = "localhost" in app_url or "127.0.0.1" in app_url
    
    if is_https and not is_local:
        try:
            await bot.set_chat_menu_button(
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
            await bot.set_chat_menu_button(
                menu_button=MenuButtonDefault()
            )
            logger.info("Reset WebApp Menu Button to default (not HTTPS or local address).")
        except Exception as e:
            logger.error(f"Failed to reset WebApp Menu Button: {e}")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
