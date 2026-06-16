import os
import sys
import asyncio
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Add parent directory to path so app packages can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.config import settings
from backend.app.database import async_session, ensure_db_exists, engine, Base
# Импортируем модели, чтобы SQLAlchemy знал о существовании таблиц
import backend.app.models
from backend.app.crud import add_userbot_session

async def main():
    print("=== ZR4K: Telethon Userbot Login CLI Helper ===")
    
    # Гарантируем, что база данных zr4k существует
    await ensure_db_exists()
    
    # Автоматически создаем все таблицы в БД перед началом работы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    api_id = settings.telegram_api_id
    api_hash = settings.telegram_api_hash
    
    if not api_id or api_hash == "YOUR_API_HASH_HERE" or api_id == 0:
        print("❌ Error: Please specify valid TELEGRAM_API_ID and TELEGRAM_API_HASH in your backend/.env file.")
        return
        
    default_phone = settings.userbot_phone
    prompt = f"Enter userbot phone number [{default_phone}]: " if default_phone else "Enter userbot phone number (e.g. +79001234567): "
    phone = input(prompt).strip() or default_phone
    if not phone:
        print("❌ Error: Phone number is required.")
        return
        
    # Create backend/sessions/ directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sessions_dir = os.path.join(base_dir, "sessions")
    os.makedirs(sessions_dir, exist_ok=True)
    
    # Sanitize phone number for session filename
    safe_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
    session_name = f"userbot_{safe_phone}"
    session_path = os.path.join(sessions_dir, session_name)
    
    print(f"⚙️ Initializing Telethon client for session: {session_name}...")
    
    client = TelegramClient(session_path, api_id, api_hash)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("\nВыберите способ авторизации:")
        print("1. По номеру телефона (ввод кода подтверждения)")
        print("2. По QR-коду (сканирование через мобильное приложение Telegram)")
        choice = input("Введите число (1 или 2, по умолчанию 1): ").strip()
        
        if choice == "2":
            print("⚙️ Инициализация входа по QR-коду...")
            try:
                import qrcode
                qr_login = await client.qr_login()
                
                # Render ASCII QR code in terminal
                qr = qrcode.QRCode()
                qr.add_data(qr_login.url)
                print("\n📱 Откройте Telegram на телефоне -> Настройки -> Устройства -> Подключить устройство")
                print("И отсканируйте этот QR-код:\n")
                qr.print_ascii()
                print(f"\nИли перейдите по ссылке: {qr_login.url}\n")
                
                try:
                    await qr_login.wait()
                    print("✅ Успешный вход через QR-код!")
                except SessionPasswordNeededError:
                    password = input("Включена двухфакторная аутентификация (2FA). Введите ваш пароль: ").strip()
                    try:
                        await client.sign_in(password=password)
                        print("✅ Успешный вход с использованием 2FA!")
                    except Exception as e:
                        print(f"❌ Ошибка входа 2FA: {str(e)}")
                        await client.disconnect()
                        return
            except Exception as e:
                print(f"❌ Ошибка авторизации по QR-коду: {str(e)}")
                await client.disconnect()
                return
        else:
            print(f"✉️ Отправка запроса на получение кода подтверждения на номер {phone}...")
            try:
                await client.send_code_request(phone)
            except Exception as e:
                print(f"❌ Не удалось отправить запрос: {str(e)}")
                await client.disconnect()
                return
                
            code = input("Введите код подтверждения, полученный в Telegram: ").strip()
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                password = input("Включена двухфакторная аутентификация (2FA). Введите ваш пароль: ").strip()
                try:
                    await client.sign_in(password=password)
                except Exception as e:
                    print(f"❌ Ошибка входа 2FA: {str(e)}")
                    await client.disconnect()
                    return
            except Exception as e:
                print(f"❌ Ошибка входа: {str(e)}")
                await client.disconnect()
                return
            
    me = await client.get_me()
    first_name = me.first_name or "Userbot"
    username = f"@{me.username}" if me.username else "No Username"
    print(f"✅ Successfully authenticated as {first_name} ({username})")
    
    # Save the session to Postgres database
    async with async_session() as db:
        try:
            await add_userbot_session(db, phone=phone, session_name=session_name)
            print("💾 Session meta successfully registered in PostgreSQL database.")
        except Exception as e:
            print(f"⚠️ Warning: Could not register session in DB (is PostgreSQL running?): {str(e)}")
            
    await client.disconnect()
    # Освобождаем пул соединений SQLAlchemy
    await engine.dispose()
    print(f"🎉 Done! Session file saved at: backend/sessions/{session_name}.session")

if __name__ == "__main__":
    asyncio.run(main())
