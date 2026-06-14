import os
import sys
import asyncio
import json
import logging
from sqlalchemy.future import select
from sqlalchemy import func
from telethon import TelegramClient, events
from telethon.errors import AuthKeyUnregisteredError, UserDeactivatedError, SessionExpiredError
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.account import UpdateNotifySettingsRequest
from telethon.tl.types import InputPeerNotifySettings, InputNotifyPeer, InputFolderPeer
from telethon.tl.functions.folders import EditPeerFoldersRequest
from aiogram import Bot

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.config import settings
from backend.app.database import async_session
from backend.app.models import User, Channel, UserChannel, Keyword, UserbotSession
from backend.app.crud import deactivate_userbot_session, save_caught_message
from backend.app.matcher import evaluate_message
from backend.app.shared import deduplicator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("zr4k.parser")

clients = {}
monitored_channels = {}
monitored_peer_ids = {}

bot = None
token = settings.telegram_bot_token
if token and token != "YOUR_BOT_TOKEN_HERE" and ":" in token:
    try:
        bot = Bot(token=token)
    except Exception as e:
        logger.error(f"❌ Failed to initialize Bot in parser: {e}")
redis_client = None


async def notify_admin(message: str):
    if bot and settings.admin_user_id:
        try:
            await bot.send_message(chat_id=settings.admin_user_id, text=f"🚨 **Системное уведомление:**\n{message}")
        except Exception as e:
            logger.error(f"Failed to send alert to admin: {str(e)}")

async def handle_session_death(session_id: int, session_name: str, phone: str, error_msg: str):
    logger.error(f"Session '{session_name}' ({phone}) has died: {error_msg}")
    async with async_session() as db:
        await deactivate_userbot_session(db, session_name)
    
    client = clients.pop(session_id, None)
    if client:
        try:
            await client.disconnect()
        except Exception:
            pass
            
    await notify_admin(
        f"Сессия юзербота `{session_name}` ({phone}) была деактивирована из-за ошибки авторизации:\n`{error_msg}`"
    )

async def process_new_message(event, client_session_id: int):
    if not event.is_channel:
        return

    chat_id = event.chat_id
    
    channel_id = monitored_peer_ids.get(chat_id)
    if not channel_id:
        chat = await event.get_chat()
        username = chat.username.lower() if getattr(chat, 'username', None) else None
        if username:
            channel_id = monitored_channels.get(username)
            if channel_id:
                monitored_peer_ids[chat_id] = channel_id
                async with async_session() as db:
                    stmt = select(Channel).where(Channel.id == channel_id)
                    res = await db.execute(stmt)
                    channel_obj = res.scalar_one_or_none()
                    if channel_obj and channel_obj.telegram_id != chat_id:
                        channel_obj.telegram_id = chat_id
                        await db.commit()

    if not channel_id:
        return

    message_id = event.message.id
    message_text = event.message.message or ""
    if not message_text:
        return

    if deduplicator.is_duplicate(channel_id, message_id):
        return

    logger.info(f"Processing message {message_id} from channel ID {channel_id}")

    async with async_session() as db:
        stmt = (
            select(UserChannel)
            .join(User, User.telegram_id == UserChannel.user_id)
            .where(
                UserChannel.channel_id == channel_id,
                UserChannel.active == True
            )
        )
        res = await db.execute(stmt)
        user_channels = res.scalars().all()

        for uc in user_channels:
            stmt_user = select(User).where(User.telegram_id == uc.user_id)
            res_user = await db.execute(stmt_user)
            user = res_user.scalar_one_or_none()
            if not user:
                continue

            stmt_kw = select(Keyword).where(
                Keyword.user_id == uc.user_id,
                Keyword.channel_id == channel_id
            )
            res_kw = await db.execute(stmt_kw)
            kws = res_kw.scalars().all()
            
            rules = [{"keyword": kw.keyword, "mode": kw.mode} for kw in kws]
            
            if evaluate_message(message_text, rules):
                stmt_chan = select(Channel).where(Channel.id == channel_id)
                res_chan = await db.execute(stmt_chan)
                chan_obj = res_chan.scalar_one_or_none()
                channel_username = chan_obj.username if chan_obj else ""
                
                if channel_username:
                    post_url = f"https://t.me/{channel_username}/{message_id}"
                else:
                    post_url = f"https://t.me/c/{str(chat_id)[4:]}/{message_id}"
                
                await save_caught_message(
                    db,
                    user_id=uc.user_id,
                    channel_id=channel_id,
                    message_id=message_id,
                    text=message_text,
                    url=post_url
                )
                
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                channel_title = chan_obj.title or channel_username or "Канал"
                notification_text = (
                    f"{channel_title}\n\n"
                    f"{message_text[:400]}{'...' if len(message_text) > 400 else ''}"
                )
                try:
                    keyboard = InlineKeyboardMarkup(
                        inline_keyboard=[[
                            InlineKeyboardButton(text="Перейти к сообщению", url=post_url)
                        ]]
                    )
                    await bot.send_message(
                        chat_id=uc.user_id,
                        text=notification_text,
                        reply_markup=keyboard,
                        parse_mode="Markdown",
                        disable_web_page_preview=True
                    )
                except Exception as e:
                    logger.error(f"Failed to send notification to user {uc.user_id}: {str(e)}")

async def setup_client_handlers(client: TelegramClient, session_id: int):
    @client.on(events.NewMessage)
    async def msg_handler(event):
        try:
            await process_new_message(event, session_id)
        except Exception as e:
            logger.error(f"Error in process_new_message: {str(e)}")

async def run_client(session_id: int, phone: str, session_name: str, api_id: int, api_hash: str):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.exists("/app/data"):
        sessions_dir = "/app/data/sessions"
    else:
        sessions_dir = os.path.join(base_dir, "sessions")
    os.makedirs(sessions_dir, exist_ok=True)
    session_path = os.path.join(sessions_dir, session_name)
    
    logger.info(f"Starting Telethon client for {session_name} at {session_path}...")
    client = TelegramClient(session_path, api_id, api_hash)
    clients[session_id] = client

    try:
        await client.connect()
        logger.info(f"Client for {session_name} connected to Telegram.")
        is_auth = await client.is_user_authorized()
        logger.info(f"Client for {session_name} authorization status: {is_auth}")
        if not is_auth:
            await handle_session_death(session_id, session_name, phone, "Session not authorized. Needs login.")
            return

        await setup_client_handlers(client, session_id)
        logger.info(f"Client for {session_name} handlers configured successfully.")
        
        await client.run_until_disconnected()

    except (AuthKeyUnregisteredError, UserDeactivatedError, SessionExpiredError) as e:
        await handle_session_death(session_id, session_name, phone, f"Telethon authorization error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in client loop for {session_name}: {str(e)}")
        if "auth" in str(e).lower() or "unregistered" in str(e).lower():
            await handle_session_death(session_id, session_name, phone, str(e))
    finally:
        logger.info(f"Disconnecting client for {session_name}...")
        try:
            await client.disconnect()
        except Exception:
            pass

async def fetch_history_direct(channels_data: list, hours: int) -> list:
    from datetime import datetime, timedelta, timezone
    offset_date = datetime.now(timezone.utc) - timedelta(hours=hours)
    all_texts = []
    
    async def fetch_channel_history(client, c_username):
        texts = []
        try:
            entity = await client.get_entity(c_username)
            c_title = getattr(entity, 'title', None) or c_username
            async for msg in client.iter_messages(entity, limit=300):
                if msg.date < offset_date:
                    break
                if msg.text:
                    texts.append({
                        "channel": c_title,
                        "text": msg.text
                    })
        except Exception as e:
            logger.error(f"Failed to fetch history for {c_username}: {str(e)}")
        return texts

    history_tasks = []
    for cdata in channels_data:
        session_id = cdata.get("session_id")
        c_username = cdata.get("username")
        if not session_id or not c_username:
            continue
        
        client = clients.get(session_id)
        if not client:
            continue
        history_tasks.append(fetch_channel_history(client, c_username))
        
    if history_tasks:
        results = await asyncio.gather(*history_tasks)
        for r_texts in results:
            all_texts.extend(r_texts)
            
    return all_texts

async def handle_control_action(data: dict):
    action = data.get("action")
    username = data.get("username", "").lower()
    channel_id = data.get("channel_id")

    if not username or not channel_id:
        return

    if not clients:
        logger.error("No active userbots available to perform actions.")
        return

    async with async_session() as db:
        stmt = (
            select(UserbotSession.id, func.count(Channel.id))
            .join(Channel, Channel.userbot_session_id == UserbotSession.id, isouter=True)
            .where(UserbotSession.is_active == True)
            .group_by(UserbotSession.id)
            .order_by(func.count(Channel.id).asc())
        )
        res = await db.execute(stmt)
        row = res.first()
        if not row:
            logger.error("No active userbot sessions registered in database.")
            return
            
        target_session_id = row[0]
        client = clients.get(target_session_id)
        if not client:
            logger.error(f"Client for session ID {target_session_id} is not running in memory.")
            return

    if action == "join":
        logger.info(f"Action JOIN: {username} on session ID {target_session_id}")
        try:
            entity = await client.get_entity(username)
            await client(JoinChannelRequest(entity))
            
            try:
                await client(UpdateNotifySettingsRequest(
                    peer=InputNotifyPeer(entity),
                    settings=InputPeerNotifySettings(mute_until=2147483647)
                ))
            except Exception as e:
                logger.warning(f"Failed to mute channel {username}: {str(e)}")
                
            try:
                from telethon.tl.types import InputPeerChannel
                peer_arg = InputPeerChannel(entity.id, entity.access_hash) if hasattr(entity, 'access_hash') else entity
                await client(EditPeerFoldersRequest(
                    folder_peers=[InputFolderPeer(peer=peer_arg, folder_id=1)]
                ))
            except Exception as e:
                logger.warning(f"Failed to archive channel {username}: {str(e)}")
            
            full_chat = await client.get_entity(entity)
            title = getattr(full_chat, 'title', None)
            telegram_id = full_chat.id
            normalized_telegram_id = int(f"-100{telegram_id}")
            
            monitored_channels[username] = channel_id
            monitored_peer_ids[normalized_telegram_id] = channel_id

            async with async_session() as db:
                stmt = select(Channel).where(Channel.id == channel_id)
                res = await db.execute(stmt)
                chan = res.scalar_one_or_none()
                if chan:
                    chan.title = title
                    chan.telegram_id = normalized_telegram_id
                    chan.userbot_session_id = target_session_id
                    await db.commit()
            
            logger.info(f"Successfully joined and registered channel: {username}")
        except Exception as e:
            logger.error(f"Failed to join channel {username}: {str(e)}")

    elif action == "leave":
        logger.info(f"Action LEAVE: {username}")
        async with async_session() as db:
            stmt = select(Channel).where(Channel.id == channel_id)
            res = await db.execute(stmt)
            chan = res.scalar_one_or_none()
            if not chan or not chan.userbot_session_id:
                return
            
            session_id = chan.userbot_session_id
            client = clients.get(session_id)
            
            if not client:
                logger.error(f"Client for session ID {session_id} not running.")
                return

            try:
                entity = await client.get_entity(username)
                await client(LeaveChannelRequest(entity))
                logger.info(f"Left channel: {username}")
                
                monitored_channels.pop(username, None)
                if chan.telegram_id:
                    monitored_peer_ids.pop(chan.telegram_id, None)

                chan.userbot_session_id = None
                chan.telegram_id = None
                await db.commit()
            except Exception as e:
                logger.error(f"Failed to leave channel {username}: {str(e)}")

async def sync_unassigned_channels():
    logger.info("Starting sync for unassigned active channels...")
    
    async with async_session() as db:
        stmt = (
            select(Channel)
            .join(UserChannel, Channel.id == UserChannel.channel_id)
            .where(UserChannel.active == True, Channel.userbot_session_id.is_(None))
            .distinct()
        )
        res = await db.execute(stmt)
        unassigned_channels = res.scalars().all()
        
    if not unassigned_channels:
        logger.info("No unassigned active channels found.")
        return
        
    logger.info(f"Found {len(unassigned_channels)} unassigned active channels. Attempting to join...")
    for ch in unassigned_channels:
        try:
            await handle_control_action({
                "action": "join",
                "username": ch.username,
                "channel_id": ch.id
            })
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Error during auto-join of {ch.username}: {str(e)}")

async def start_parser():
    logger.info("Starting ZR4K Parser Bot pool...")
    
    try:
        while True:
            try:
                async with async_session() as db:
                    # 1. Update monitored channels mappings from DB
                    stmt_chan = select(Channel).where(Channel.userbot_session_id.isnot(None))
                    res_chan = await db.execute(stmt_chan)
                    channels_db = res_chan.scalars().all()
                    
                    # Update local caches
                    current_monitored_usernames = set()
                    current_monitored_peer_ids = set()
                    for ch in channels_db:
                        monitored_channels[ch.username] = ch.id
                        current_monitored_usernames.add(ch.username)
                        if ch.telegram_id:
                            monitored_peer_ids[ch.telegram_id] = ch.id
                            current_monitored_peer_ids.add(ch.telegram_id)
                            
                    # Remove dead/deleted channels from local memory collections
                    for username in list(monitored_channels.keys()):
                        if username not in current_monitored_usernames:
                            monitored_channels.pop(username, None)
                    for peer_id in list(monitored_peer_ids.keys()):
                        if peer_id not in current_monitored_peer_ids:
                            monitored_peer_ids.pop(peer_id, None)
                            
                    # 2. Query active sessions from DB
                    stmt_sessions = select(UserbotSession).where(UserbotSession.is_active == True)
                    res_sessions = await db.execute(stmt_sessions)
                    active_sessions = res_sessions.scalars().all()
                    
                # 3. Start client tasks for newly activated sessions
                for sess in active_sessions:
                    if sess.id not in clients:
                        logger.info(f"Detected new active userbot session in DB: {sess.session_name}. Starting client...")
                        # Spawn run_client in background as a task
                        asyncio.create_task(
                            run_client(
                                session_id=sess.id,
                                phone=sess.phone,
                                session_name=sess.session_name,
                                api_id=settings.telegram_api_id,
                                api_hash=settings.telegram_api_hash
                            )
                        )
                        
                # 4. Sync and auto-join unassigned active channels
                await sync_unassigned_channels()
                
            except Exception as e:
                logger.error(f"Error in start_parser loop cycle: {e}")
                
            # Wait 30 seconds before next sync cycle
            await asyncio.sleep(30)
            
    except asyncio.CancelledError:
        logger.info("Parser Bot shutting down...")
    finally:
        if bot is not None:
            await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(start_parser())
    except KeyboardInterrupt:
        logger.info("Parser Bot stopped by user.")