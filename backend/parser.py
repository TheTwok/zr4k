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
import redis.asyncio as aioredis
from aiogram import Bot

# Add parent directory to path so app packages can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.config import settings
from backend.app.database import async_session
from backend.app.models import User, Channel, UserChannel, Keyword, UserbotSession
from backend.app.crud import deactivate_userbot_session, save_caught_message
from backend.app.matcher import evaluate_message

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("zr4k.parser")

# Global dict of active Telethon clients: {session_id: TelegramClient}
clients = {}
# Mapping from channel_username (lowercase) to database Channel id: {username: channel_id}
monitored_channels = {}
# Mapping from resolved telegram_id (int) to database Channel id: {telegram_id: channel_id}
monitored_peer_ids = {}

# Client Bot instance for notifications
bot = Bot(token=settings.telegram_bot_token)
redis_client = None


async def notify_admin(message: str):
    """
    Helper to send a system alert to the admin.
    """
    if settings.admin_user_id:
        try:
            await bot.send_message(chat_id=settings.admin_user_id, text=f"🚨 **Системное уведомление:**\n{message}")
        except Exception as e:
            logger.error(f"Failed to send alert to admin: {str(e)}")

async def handle_session_death(session_id: int, session_name: str, phone: str, error_msg: str):
    """
    Deactivates a dead session in DB and notifies admin.
    """
    logger.error(f"Session '{session_name}' ({phone}) has died: {error_msg}")
    async with async_session() as db:
        await deactivate_userbot_session(db, session_name)
    
    # Close client if running
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
    """
    Handles a new message event from Telethon.
    """
    if not event.is_channel:
        return

    chat_id = event.chat_id # e.g. -100123456789
    
    # 1. Check if channel is monitored
    channel_id = monitored_peer_ids.get(chat_id)
    if not channel_id:
        # Fallback to check by username if peer ID is not resolved yet
        chat = await event.get_chat()
        username = chat.username.lower() if getattr(chat, 'username', None) else None
        if username:
            channel_id = monitored_channels.get(username)
            if channel_id:
                # Update peer ID in DB and cache
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

    # 2. De-duplication check in Redis
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(settings.redis_url)
    dup_key = f"zr4k:msg_dup:{channel_id}:{message_id}"
    is_duplicate = await redis_client.set(dup_key, "1", ex=300, nx=True) # 5 minutes TTL
    if not is_duplicate:
        # Already processed
        return

    logger.info(f"Processing message {message_id} from channel ID {channel_id}")

    # 3. Retrieve active user channels and their keywords
    async with async_session() as db:
        # Get users tracking this channel actively
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
            # Check user subscription status
            stmt_user = select(User).where(User.telegram_id == uc.user_id)
            res_user = await db.execute(stmt_user)
            user = res_user.scalar_one_or_none()
            if not user:
                continue

            # Free users are limited to 1 channel and 5 keywords. Pro users to 100/200.
            # (Enforced at entry, but we can verify is_pro if needed)
            
            # Fetch user keywords for this channel
            stmt_kw = select(Keyword).where(
                Keyword.user_id == uc.user_id,
                Keyword.channel_id == channel_id
            )
            res_kw = await db.execute(stmt_kw)
            kws = res_kw.scalars().all()
            
            rules = [{"keyword": kw.keyword, "mode": kw.mode} for kw in kws]
            
            # 4. Evaluate message against user's filters
            if evaluate_message(message_text, rules):
                # Generate post URL
                # Fetch channel info from cache or DB to form the URL
                stmt_chan = select(Channel).where(Channel.id == channel_id)
                res_chan = await db.execute(stmt_chan)
                chan_obj = res_chan.scalar_one_or_none()
                channel_username = chan_obj.username if chan_obj else ""
                
                if channel_username:
                    post_url = f"https://t.me/{channel_username}/{message_id}"
                else:
                    # Private channels or missing username link format
                    post_url = f"https://t.me/c/{str(chat_id)[4:]}/{message_id}"
                
                # Save caught message
                await save_caught_message(
                    db,
                    user_id=uc.user_id,
                    channel_id=channel_id,
                    message_id=message_id,
                    text=message_text,
                    url=post_url
                )
                
                # 5. Send real-time notification
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
    """
    Registers the message handler for a Telethon client.
    """
    @client.on(events.NewMessage)
    async def msg_handler(event):
        try:
            await process_new_message(event, session_id)
        except Exception as e:
            logger.error(f"Error in process_new_message: {str(e)}")

async def run_client(session_id: int, phone: str, session_name: str, api_id: int, api_hash: str):
    """
    Starts and keeps running a single Telethon client.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    session_path = os.path.join(base_dir, "sessions", session_name)
    
    logger.info(f"Starting Telethon client for {session_name}...")
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

        # Setup message handler
        await setup_client_handlers(client, session_id)
        logger.info(f"Client for {session_name} handlers configured successfully.")
        
        # Keep client running
        await client.run_until_disconnected()

    except (AuthKeyUnregisteredError, UserDeactivatedError, SessionExpiredError) as e:
        await handle_session_death(session_id, session_name, phone, f"Telethon authorization error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in client loop for {session_name}: {str(e)}")
        # Check if auth/network error is persistent
        if "auth" in str(e).lower() or "unregistered" in str(e).lower():
            await handle_session_death(session_id, session_name, phone, str(e))

async def handle_control_action(data: dict):
    """
    Processes join/leave/fetch_history actions from the Redis queue.
    """
    action = data.get("action")

    if action == "fetch_history":
        request_id = data.get("request_id")
        channels_data = data.get("channels_data", [])
        hours = data.get("hours", 24)
        logger.info(f"Action FETCH_HISTORY: {hours}h for {len(channels_data)} channels (req: {request_id})")
        
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
                
        # Send result back via Redis
        try:
            r = aioredis.from_url(settings.redis_url)
            await r.set(f"zr4k:rpc:res:{request_id}", json.dumps(all_texts), ex=60)
            await r.aclose()
            logger.info(f"Published history result for req: {request_id} ({len(all_texts)} msgs)")
        except Exception as e:
            logger.error(f"Failed to return RPC result: {str(e)}")
        return

    # Validations for join/leave
    username = data.get("username", "").lower()
    channel_id = data.get("channel_id")

    if not username or not channel_id:
        return

    # Choose an active client
    if not clients:
        logger.error("No active userbots available to perform actions.")
        return

    # For scaling, choose client with lowest channel count in DB
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
            
            # Join channel
            await client(JoinChannelRequest(entity))
            
            # Try to mute channel (optional)
            try:
                await client(UpdateNotifySettingsRequest(
                    peer=InputNotifyPeer(entity),
                    settings=InputPeerNotifySettings(mute_until=2147483647)
                ))
            except Exception as e:
                logger.warning(f"Failed to mute channel {username}: {str(e)}")
                
            # Try to archive channel (optional)
            try:
                from telethon.tl.types import InputPeerChannel
                peer_arg = InputPeerChannel(entity.id, entity.access_hash) if hasattr(entity, 'access_hash') else entity
                await client(EditPeerFoldersRequest(
                    folder_peers=[InputFolderPeer(peer=peer_arg, folder_id=1)]
                ))
            except Exception as e:
                logger.warning(f"Failed to archive channel {username}: {str(e)}")
            
            # Fetch channel details
            full_chat = await client.get_entity(entity)
            title = getattr(full_chat, 'title', None)
            telegram_id = full_chat.id
            normalized_telegram_id = int(f"-100{telegram_id}")
            
            # Update cache and database
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
            # If the channel is invalid or doesn't exist, we should mark it as inactive or handle it
            # so the user sees an error (done via frontend/backend validation where possible).

    elif action == "leave":
        logger.info(f"Action LEAVE: {username}")
        # Find which client holds this channel
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
                
                # Remove from cache
                monitored_channels.pop(username, None)
                if chan.telegram_id:
                    monitored_peer_ids.pop(chan.telegram_id, None)

                # Reset session assignment in DB
                chan.userbot_session_id = None
                chan.telegram_id = None
                await db.commit()
            except Exception as e:
                logger.error(f"Failed to leave channel {username}: {str(e)}")

async def sync_unassigned_channels():
    """
    Finds channels that have active subscribers but no userbot_session_id,
    and tries to join them using an active client.
    """
    await asyncio.sleep(5) # Wait for clients to connect
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

async def listen_redis_control():
    """
    Subscribes to Redis control PubSub to handle dynamic joins/leaves.
    """
    logger.info("Initializing Redis PubSub listener...")
    r = aioredis.from_url(settings.redis_url)
    pubsub = r.pubsub()
    await pubsub.subscribe("zr4k:parser:control")
    
    try:
        async for message in pubsub.listen():
            logger.info(f"Redis PubSub listener received raw message: {message}")
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    logger.info(f"Parsed PubSub command data: {data}")
                    await handle_control_action(data)
                except Exception as e:
                    logger.error(f"Error handling control action: {str(e)}")
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe("zr4k:parser:control")
        await r.aclose()

async def start_parser():
    logger.info("Starting ZR4K Parser Bot pool...")
    
    # 1. Warm up channel cache
    async with async_session() as db:
        stmt_chan = select(Channel).where(Channel.userbot_session_id.isnot(None))
        res_chan = await db.execute(stmt_chan)
        channels_db = res_chan.scalars().all()
        for ch in channels_db:
            monitored_channels[ch.username] = ch.id
            if ch.telegram_id:
                monitored_peer_ids[ch.telegram_id] = ch.id
                
        # Get active sessions
        stmt_sessions = select(UserbotSession).where(UserbotSession.is_active == True)
        res_sessions = await db.execute(stmt_sessions)
        active_sessions = res_sessions.scalars().all()
        
    if not active_sessions:
        logger.warning("No active userbot sessions found in database. Parser running but idle.")
        logger.info("To add a session, run: backend/login_userbot.py")

    # 2. Launch each client in background
    tasks = []
    for sess in active_sessions:
        task = asyncio.create_task(
            run_client(
                session_id=sess.id,
                phone=sess.phone,
                session_name=sess.session_name,
                api_id=settings.telegram_api_id,
                api_hash=settings.telegram_api_hash
            )
        )
        tasks.append(task)

    # 3. Launch Redis control listener
    control_task = asyncio.create_task(listen_redis_control())
    tasks.append(control_task)

    # 4. Launch unassigned channels sync
    sync_task = asyncio.create_task(sync_unassigned_channels())
    tasks.append(sync_task)

    # Keep running
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        logger.info("Parser Bot shutting down...")
    finally:
        # Close bot session
        await bot.session.close()
        global redis_client
        if redis_client:
            await redis_client.aclose()

if __name__ == "__main__":
    try:
        asyncio.run(start_parser())
    except KeyboardInterrupt:
        logger.info("Parser Bot stopped by user.")
