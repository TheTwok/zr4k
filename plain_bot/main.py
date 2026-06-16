from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from html import escape

import uvicorn
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    LabeledPrice,
    MenuButtonDefault,
    Message,
    PreCheckoutQuery,
)
from aiogram.enums import ParseMode
from fastapi import FastAPI

from backend.app.config import settings
from backend.parser import start_parser
from plain_bot import keyboards as kb
from plain_bot import services
from plain_bot.states import AdminPromoStates, KeywordStates, PromoStates, SourceStates


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("zr4k.plain_bot")

router = Router()
health_app = FastAPI(title="ZR4K Plain Bot")


def get_port() -> int:
    for key in ("PORT", "APP_PORT", "WEB_PORT", "BOTHOST_PORT"):
        value = os.getenv(key)
        if not value:
            continue
        try:
            return int(value.strip("'\" "))
        except ValueError:
            logger.warning("Ignoring invalid %s value: %r", key, value)
    return 8000


@health_app.get("/")
@health_app.get("/health")
async def health() -> dict:
    return {"status": "ok", "mode": "plain_bot"}


async def safe_edit(callback: CallbackQuery, text: str, reply_markup=None) -> None:
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup, disable_web_page_preview=True)
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            return
        await callback.message.answer(text, reply_markup=reply_markup, disable_web_page_preview=True)


async def require_user_from_message(message: Message) -> services.User | None:
    user = await services.ensure_user(message.from_user)
    if user.is_banned:
        await message.answer("Ваш аккаунт заблокирован. Доступ к боту закрыт.")
        return None
    return user


async def require_user_from_callback(callback: CallbackQuery) -> services.User | None:
    user = await services.ensure_user(callback.from_user)
    if user.is_banned:
        await callback.answer("Аккаунт заблокирован.", show_alert=True)
        return None
    return user


async def show_main(target: Message | CallbackQuery, user: services.User) -> None:
    text = (
        "<b>ZR4K</b>\n"
        "Бот для мониторинга Telegram-каналов в реальном времени и умной ИИ-аналитики.\n\n"
        "<b>Что вы можете делать:</b>\n"
        "• Подключать Telegram-каналы как источники.\n"
        "• Настраивать точные, смысловые и исключающие фильтры.\n"
        "• Получать найденные совпадения прямо в чат.\n"
        "• Создавать ручные и автоматические AI-дайджесты.\n\n"
        "Выберите раздел ниже."
    )
    markup = kb.main_menu(services.is_admin(user))
    if isinstance(target, CallbackQuery):
        await safe_edit(target, text, markup)
        await target.answer()
    else:
        await target.answer(text, reply_markup=markup)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = await require_user_from_message(message)
    if user:
        await show_main(message, user)


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = await require_user_from_message(message)
    if user:
        await show_main(message, user)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    user = await require_user_from_message(message)
    if not user:
        return
    await message.answer(
        "<b>Помощь</b>\n"
        "Источники: добавляйте публичные каналы по @username или t.me/username.\n"
        "Фильтры: задавайте слова, фразы, смысловой поиск или исключения.\n"
        "Совпадения приходят сообщениями и остаются в этом чате.\n"
        "Дайджест: ручная и расписанная AI-сводка для PRO.\n"
        "PRO: оплата Stars или промокод.",
        reply_markup=kb.back_main(),
    )


@router.callback_query(F.data == "act:cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user = await require_user_from_callback(callback)
    if user:
        await show_main(callback, user)


@router.callback_query(F.data == "m:main")
async def menu_main(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user = await require_user_from_callback(callback)
    if user:
        await show_main(callback, user)


@router.callback_query(F.data == "m:overview")
async def menu_overview(callback: CallbackQuery) -> None:
    user = await require_user_from_callback(callback)
    if not user:
        return
    data = await services.overview(user.telegram_id)
    profile = data["user"]
    text = (
        "<b>Обзор</b>\n"
        f"Тариф: {'PRO' if profile and profile.is_pro else 'Free'}\n"
        f"PRO до: {services.dt_text(profile.pro_expires_at if profile else None)}\n\n"
        f"Источники: {data['sources']}\n"
        f"Фильтры: {data['keywords']}\n"
        f"Найдено сообщений: {data['messages']}"
    )
    await safe_edit(callback, text, kb.back_main())
    await callback.answer()


@router.callback_query(F.data == "m:help")
async def menu_help(callback: CallbackQuery) -> None:
    user = await require_user_from_callback(callback)
    if not user:
        return
    await safe_edit(
        callback,
        "<b>Помощь</b>\n"
        "Работа строится от источника к фильтрам.\n\n"
        "1. Добавьте канал в разделе Источники.\n"
        "2. Добавьте фильтры для выбранного канала.\n"
        "3. Совпадения будут приходить сообщениями от бота и сохраняться в чате.\n"
        "4. В разделе Дайджест можно собрать AI-сводку.",
        kb.back_main(),
    )
    await callback.answer()


@router.callback_query(F.data == "m:sources")
async def menu_sources(callback: CallbackQuery) -> None:
    user = await require_user_from_callback(callback)
    if not user:
        return
    sources = await services.list_sources(user.telegram_id)
    lines = ["<b>Источники</b>"]
    if sources:
        lines.extend(f"{idx}. @{escape(source.username)}" for idx, source in enumerate(sources, start=1))
    else:
        lines.append("Пока нет источников.")
    await safe_edit(callback, "\n".join(lines), kb.sources_menu())
    await callback.answer()


@router.callback_query(F.data == "src:add")
async def source_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    user = await require_user_from_callback(callback)
    if not user:
        return
    await state.set_state(SourceStates.waiting_link)
    await safe_edit(
        callback,
        "<b>Новый источник</b>\n"
        "Отправьте @username или ссылку вида t.me/username.\n"
        "Поддерживаются только публичные открытые каналы.",
        kb.cancel_menu(),
    )
    await callback.answer()


@router.message(SourceStates.waiting_link)
async def source_add_finish(message: Message, state: FSMContext) -> None:
    user = await require_user_from_message(message)
    if not user:
        return
    try:
        channel = await services.add_source(user.telegram_id, message.text or "")
        await state.clear()
        await message.answer(
            f"Источник @{escape(channel.username)} добавлен.\n"
            "Если userbot-сессия активна, парсер подключит канал автоматически.",
            reply_markup=kb.sources_menu(),
        )
    except Exception as exc:
        await message.answer(f"Не удалось добавить источник: {escape(services.error_text(exc))}", reply_markup=kb.cancel_menu())


@router.callback_query(F.data == "src:list")
async def source_list(callback: CallbackQuery) -> None:
    await menu_sources(callback)


@router.callback_query(F.data == "src:del")
async def source_delete_menu(callback: CallbackQuery) -> None:
    user = await require_user_from_callback(callback)
    if not user:
        return
    sources = await services.list_sources(user.telegram_id)
    if not sources:
        await safe_edit(callback, "<b>Удаление источника</b>\nНет активных источников.", kb.sources_menu())
        await callback.answer()
        return
    rows = [[kb.button(f"@{source.username}", f"src:rm:{source.id}", style="danger", icon="delete")] for source in sources]
    rows.append([kb.button("Назад", "m:sources", icon="back")])
    await safe_edit(callback, "<b>Удаление источника</b>\nВыберите источник.", kb.keyboard(rows))
    await callback.answer()


@router.callback_query(F.data.startswith("src:rm:"))
async def source_remove(callback: CallbackQuery) -> None:
    user = await require_user_from_callback(callback)
    if not user:
        return
    channel_id = int(callback.data.split(":")[2])
    try:
        username = await services.remove_source(user.telegram_id, channel_id)
        await safe_edit(callback, f"Источник @{escape(username)} удален.", kb.sources_menu())
    except Exception as exc:
        await safe_edit(callback, f"Не удалось удалить источник: {escape(services.error_text(exc))}", kb.sources_menu())
    await callback.answer()


@router.callback_query(F.data == "m:filters")
async def menu_filters(callback: CallbackQuery) -> None:
    user = await require_user_from_callback(callback)
    if not user:
        return
    sources = await services.list_sources(user.telegram_id)
    if not sources:
        await safe_edit(
            callback,
            "<b>Фильтры</b>\nСначала добавьте источник.",
            kb.keyboard([[kb.button("Добавить источник", "src:add", style="success", icon="add")], [kb.button("В главное меню", "m:main", icon="back")]]),
        )
        await callback.answer()
        return
    rows = [[kb.button(f"@{source.username}", f"flt:c:{source.id}", style="primary", icon="sources")] for source in sources]
    rows.append([kb.button("В главное меню", "m:main", icon="back")])
    await safe_edit(callback, "<b>Фильтры</b>\nВыберите источник.", kb.keyboard(rows))
    await callback.answer()


async def show_channel_filters(callback: CallbackQuery, user_id: int, channel_id: int) -> None:
    channel, keywords = await services.list_keywords(user_id, channel_id)
    lines = [f"<b>Фильтры: @{escape(channel.username)}</b>"]
    if not keywords:
        lines.append("Фильтров пока нет.")
    else:
        for idx, item in enumerate(keywords, start=1):
            mode = services.MODE_LABELS.get(item.mode, item.mode)
            lines.append(f"{idx}. {escape(item.keyword)} — {escape(mode)}")
    rows = [
        [kb.button("Добавить фильтр", f"kw:add:{channel_id}", style="success", icon="add")],
        [kb.button("Удалить фильтр", f"kw:del:{channel_id}", style="danger", icon="delete")],
        [kb.button("К источникам", "m:filters", icon="back")],
    ]
    await safe_edit(callback, "\n".join(lines), kb.keyboard(rows))


@router.callback_query(F.data.startswith("flt:c:"))
async def filter_channel(callback: CallbackQuery) -> None:
    user = await require_user_from_callback(callback)
    if not user:
        return
    channel_id = int(callback.data.split(":")[2])
    try:
        await show_channel_filters(callback, user.telegram_id, channel_id)
    except Exception as exc:
        await safe_edit(callback, f"Не удалось открыть фильтры: {escape(services.error_text(exc))}", kb.back_main())
    await callback.answer()


@router.callback_query(F.data.startswith("kw:add:"))
async def keyword_add_mode(callback: CallbackQuery) -> None:
    user = await require_user_from_callback(callback)
    if not user:
        return
    channel_id = int(callback.data.split(":")[2])
    rows = [
        [kb.button("Смысловой", f"kw:m:{channel_id}:semantic", style="primary", icon="filters")],
        [kb.button("Точная фраза", f"kw:m:{channel_id}:exact_phrase", style="primary", icon="filters")],
        [kb.button("Точное слово", f"kw:m:{channel_id}:exact_word", style="primary", icon="filters")],
        [kb.button("Исключение", f"kw:m:{channel_id}:exclude", style="primary", icon="filters")],
        [kb.button("Назад", f"flt:c:{channel_id}", icon="back")],
    ]
    await safe_edit(callback, "<b>Тип фильтра</b>\nВыберите режим поиска.", kb.keyboard(rows))
    await callback.answer()


@router.callback_query(F.data.startswith("kw:m:"))
async def keyword_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    user = await require_user_from_callback(callback)
    if not user:
        return
    _, _, channel_id, mode = callback.data.split(":", 3)
    await state.set_state(KeywordStates.waiting_keyword)
    await state.update_data(channel_id=int(channel_id), mode=mode)
    await safe_edit(
        callback,
        f"<b>Новый фильтр</b>\nРежим: {escape(services.MODE_LABELS.get(mode, mode))}\n\nОтправьте слово или фразу.",
        kb.cancel_menu(),
    )
    await callback.answer()


@router.message(KeywordStates.waiting_keyword)
async def keyword_add_finish(message: Message, state: FSMContext) -> None:
    user = await require_user_from_message(message)
    if not user:
        return
    data = await state.get_data()
    channel_id = int(data["channel_id"])
    mode = str(data["mode"])
    try:
        item = await services.add_keyword(user.telegram_id, channel_id, message.text or "", mode)
        await state.clear()
        await message.answer(
            f"Фильтр добавлен: {escape(item.keyword)} — {escape(services.MODE_LABELS.get(item.mode, item.mode))}.",
            reply_markup=kb.keyboard([[kb.button("Открыть фильтры", f"flt:c:{channel_id}", style="primary", icon="filters")], [kb.button("В главное меню", "m:main", icon="back")]]),
        )
    except Exception as exc:
        await message.answer(f"Не удалось добавить фильтр: {escape(services.error_text(exc))}", reply_markup=kb.cancel_menu())


@router.callback_query(F.data.startswith("kw:del:"))
async def keyword_delete_menu(callback: CallbackQuery) -> None:
    user = await require_user_from_callback(callback)
    if not user:
        return
    channel_id = int(callback.data.split(":")[2])
    try:
        _, keywords = await services.list_keywords(user.telegram_id, channel_id)
    except Exception as exc:
        await safe_edit(callback, f"Не удалось открыть фильтры: {escape(services.error_text(exc))}", kb.back_main())
        await callback.answer()
        return
    if not keywords:
        await safe_edit(callback, "Нет фильтров для удаления.", kb.keyboard([[kb.button("Назад", f"flt:c:{channel_id}", icon="back")]]))
        await callback.answer()
        return
    rows = [
        [kb.button(f"{services.clip(item.keyword, 36)} — {services.MODE_LABELS.get(item.mode, item.mode)}", f"kw:rm:{item.id}:{channel_id}", style="danger", icon="delete")]
        for item in keywords
    ]
    rows.append([kb.button("Назад", f"flt:c:{channel_id}", icon="back")])
    await safe_edit(callback, "<b>Удаление фильтра</b>\nВыберите запись.", kb.keyboard(rows))
    await callback.answer()


@router.callback_query(F.data.startswith("kw:rm:"))
async def keyword_delete(callback: CallbackQuery) -> None:
    user = await require_user_from_callback(callback)
    if not user:
        return
    _, _, keyword_id, channel_id = callback.data.split(":")
    await services.delete_keyword(user.telegram_id, int(keyword_id))
    await safe_edit(callback, "Фильтр удален.", kb.keyboard([[kb.button("Открыть фильтры", f"flt:c:{channel_id}", style="primary", icon="filters")]]))
    await callback.answer()


@router.callback_query(F.data == "m:digest")
async def menu_digest(callback: CallbackQuery) -> None:
    user = await require_user_from_callback(callback)
    if not user:
        return
    text = (
        "<b>Дайджест</b>\n"
        "Здесь настраивается отправка дайджестов в чат.\n"
        "Ручная AI-сводка и расписание доступны на PRO."
    )
    await safe_edit(callback, text, kb.digest_menu(user.is_pro))
    await callback.answer()


@router.callback_query(F.data == "dig:g")
async def digest_generate_start(callback: CallbackQuery) -> None:
    user = await require_user_from_callback(callback)
    if not user:
        return
    if not user.is_pro:
        await callback.answer("Доступно только на PRO.", show_alert=True)
        return
    await safe_edit(callback, "<b>Период дайджеста</b>\nВыберите интервал.", kb.period_menu())
    await callback.answer()


@router.callback_query(F.data.startswith("dig:p:"))
async def digest_generate_finish(callback: CallbackQuery) -> None:
    user = await require_user_from_callback(callback)
    if not user:
        return
    hours = int(callback.data.split(":")[2])
    await safe_edit(callback, "Готовлю дайджест. Это может занять до минуты.", None)
    await callback.answer()
    try:
        text = await services.generate_digest(user.telegram_id, hours)
        await callback.message.answer(
            f"<b>Дайджест за {hours} ч.</b>\n\n{escape(text)}",
            reply_markup=kb.digest_menu(True),
        )
    except Exception as exc:
        await callback.message.answer(f"Не удалось создать дайджест: {escape(services.error_text(exc))}", reply_markup=kb.digest_menu(user.is_pro))


@router.callback_query(F.data == "dig:sched")
async def schedule_sources(callback: CallbackQuery) -> None:
    user = await require_user_from_callback(callback)
    if not user:
        return
    if not user.is_pro:
        await callback.answer("Расписание доступно только на PRO.", show_alert=True)
        return
    sources = await services.list_sources(user.telegram_id)
    if not sources:
        await safe_edit(callback, "<b>Расписание</b>\nСначала добавьте источник.", kb.digest_menu(user.is_pro))
        await callback.answer()
        return
    rows = [[kb.button(f"@{source.username}", f"sch:c:{source.id}", style="primary", icon="sources")] for source in sources]
    rows.append([kb.button("Назад", "m:digest", icon="back")])
    await safe_edit(callback, "<b>Расписание</b>\nВыберите источник.", kb.keyboard(rows))
    await callback.answer()


@router.callback_query(F.data.startswith("sch:c:"))
async def schedule_time(callback: CallbackQuery) -> None:
    user = await require_user_from_callback(callback)
    if not user:
        return
    channel_id = int(callback.data.split(":")[2])
    rows = [
        [kb.button("08:00", f"sch:t:{channel_id}:08", style="primary", icon="schedule"), kb.button("09:00", f"sch:t:{channel_id}:09", style="primary", icon="schedule")],
        [kb.button("12:00", f"sch:t:{channel_id}:12", style="primary", icon="schedule"), kb.button("18:00", f"sch:t:{channel_id}:18", style="primary", icon="schedule")],
        [kb.button("Отключить", f"sch:off:{channel_id}", style="danger", icon="cancel")],
        [kb.button("Назад", "dig:sched", icon="back")],
    ]
    await safe_edit(callback, "<b>Расписание</b>\nВыберите время по часовому поясу аккаунта.", kb.keyboard(rows))
    await callback.answer()


@router.callback_query(F.data.startswith("sch:t:"))
async def schedule_days(callback: CallbackQuery) -> None:
    user = await require_user_from_callback(callback)
    if not user:
        return
    _, _, channel_id, hour = callback.data.split(":")
    rows = [
        [kb.button(label, f"sch:set:{channel_id}:{hour}:{preset}", style="success", icon="generate")]
        for preset, (label, _) in services.DAY_PRESETS.items()
    ]
    rows.append([kb.button("Назад", f"sch:c:{channel_id}", icon="back")])
    await safe_edit(callback, "<b>Расписание</b>\nВыберите дни отправки.", kb.keyboard(rows))
    await callback.answer()


@router.callback_query(F.data.startswith("sch:set:"))
async def schedule_set(callback: CallbackQuery) -> None:
    user = await require_user_from_callback(callback)
    if not user:
        return
    _, _, channel_id, hour, preset = callback.data.split(":")
    label, days = services.DAY_PRESETS[preset]
    await services.set_schedule(user.telegram_id, int(channel_id), f"{hour}:00", days)
    await safe_edit(callback, f"Расписание сохранено: {hour}:00, {escape(label)}.", kb.digest_menu(user.is_pro))
    await callback.answer()


@router.callback_query(F.data.startswith("sch:off:"))
async def schedule_off(callback: CallbackQuery) -> None:
    user = await require_user_from_callback(callback)
    if not user:
        return
    channel_id = int(callback.data.split(":")[2])
    await services.set_schedule(user.telegram_id, channel_id, None, None)
    await safe_edit(callback, "Расписание отключено.", kb.digest_menu(user.is_pro))
    await callback.answer()


@router.callback_query(F.data == "m:pro")
async def menu_pro(callback: CallbackQuery) -> None:
    user = await require_user_from_callback(callback)
    if not user:
        return
    text = (
        "<b>PRO</b>\n"
        f"Статус: {'активен' if user.is_pro else 'не активен'}\n"
        f"Действует до: {services.dt_text(user.pro_expires_at)}\n\n"
        "PRO открывает до 100 источников, до 200 фильтров и AI-дайджесты."
    )
    await safe_edit(callback, text, kb.pro_menu(user.is_pro))
    await callback.answer()


@router.callback_query(F.data == "pro:promo")
async def promo_start(callback: CallbackQuery, state: FSMContext) -> None:
    user = await require_user_from_callback(callback)
    if not user:
        return
    await state.set_state(PromoStates.waiting_code)
    await safe_edit(callback, "<b>Промокод</b>\nОтправьте код одним сообщением.", kb.cancel_menu())
    await callback.answer()


@router.message(PromoStates.waiting_code)
async def promo_finish(message: Message, state: FSMContext) -> None:
    user = await require_user_from_message(message)
    if not user:
        return
    try:
        updated = await services.activate_promo(user.telegram_id, message.text or "")
        await state.clear()
        await message.answer(f"Промокод активирован. PRO до: {services.dt_text(updated.pro_expires_at)}.", reply_markup=kb.pro_menu(True))
    except Exception as exc:
        await message.answer(f"Не удалось активировать промокод: {escape(services.error_text(exc))}", reply_markup=kb.cancel_menu())


@router.callback_query(F.data == "pro:buy")
async def pro_buy(callback: CallbackQuery) -> None:
    user = await require_user_from_callback(callback)
    if not user:
        return
    await callback.message.answer_invoice(
        title="ZR4K PRO на 30 дней",
        description="Расширенные лимиты и AI-дайджесты.",
        payload="pro_subscription_30",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="ZR4K PRO", amount=50)],
        start_parameter="buy_pro_stars",
    )
    await callback.answer()


@router.pre_checkout_query()
async def checkout(query: PreCheckoutQuery) -> None:
    if query.invoice_payload == "pro_subscription_30":
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="Некорректный платеж.")


@router.message(F.successful_payment)
async def payment_success(message: Message) -> None:
    if message.successful_payment.invoice_payload != "pro_subscription_30":
        return
    await services.save_payment(message.from_user.id, message.successful_payment.total_amount)
    await message.answer("Оплата принята. PRO активирован на 30 дней.", reply_markup=kb.pro_menu(True))


async def require_admin(callback: CallbackQuery) -> services.User | None:
    user = await require_user_from_callback(callback)
    if not user:
        return None
    if not services.is_admin(user):
        await callback.answer("Недостаточно прав.", show_alert=True)
        return None
    return user


@router.callback_query(F.data == "m:admin")
async def menu_admin(callback: CallbackQuery) -> None:
    user = await require_admin(callback)
    if not user:
        return
    await safe_edit(callback, "<b>Админ</b>\nВыберите раздел.", kb.admin_menu())
    await callback.answer()


@router.callback_query(F.data == "adm:stats")
async def admin_stats(callback: CallbackQuery) -> None:
    if not await require_admin(callback):
        return
    stats = await services.admin_stats()
    text = (
        "<b>Статистика</b>\n"
        f"Пользователи: {stats['users']}\n"
        f"PRO: {stats['pro']}\n"
        f"Источники: {stats['channels']}\n"
        f"Фильтры: {stats['keywords']}\n"
        f"Сообщения: {stats['messages']}\n"
        f"Доход Stars: {stats['income']}\n"
        f"AI-вызовы: {stats['ai_calls']}"
    )
    await safe_edit(callback, text, kb.admin_menu())
    await callback.answer()


@router.callback_query(F.data.startswith("adm:users:"))
async def admin_users(callback: CallbackQuery) -> None:
    if not await require_admin(callback):
        return
    offset = int(callback.data.split(":")[2])
    users = await services.admin_users(offset)
    if not users:
        await safe_edit(callback, "Пользователи не найдены.", kb.admin_menu())
        await callback.answer()
        return
    rows = [
        [kb.button(f"{'PRO ' if item.is_pro else ''}{item.username or item.telegram_id}", f"adm:u:{item.telegram_id}", style="primary", icon="users")]
        for item in users
    ]
    nav = []
    if offset >= 8:
        nav.append(kb.button("Назад", f"adm:users:{max(0, offset - 8)}", icon="back"))
    if len(users) == 8:
        nav.append(kb.button("Дальше", f"adm:users:{offset + 8}", icon="next"))
    if nav:
        rows.append(nav)
    rows.append([kb.button("В админку", "m:admin", icon="admin")])
    await safe_edit(callback, "<b>Пользователи</b>", kb.keyboard(rows))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:u:"))
async def admin_user_card(callback: CallbackQuery) -> None:
    if not await require_admin(callback):
        return
    user_id = int(callback.data.split(":")[2])
    try:
        user, sources_count, messages_count = await services.admin_user_details(user_id)
        text = (
            "<b>Пользователь</b>\n"
            f"ID: <code>{user.telegram_id}</code>\n"
            f"Username: {escape('@' + user.username) if user.username else 'нет'}\n"
            f"PRO до: {services.dt_text(user.pro_expires_at)}\n"
            f"Заблокирован: {'да' if user.is_banned else 'нет'}\n"
            f"Источники: {sources_count}\n"
            f"Сообщения: {messages_count}"
        )
        rows = [
            [kb.button("PRO 30", f"adm:pro:{user_id}:30", style="success", icon="pro"), kb.button("PRO 90", f"adm:pro:{user_id}:90", style="success", icon="pro")],
            [kb.button("Снять PRO", f"adm:pro:{user_id}:0", style="danger", icon="delete")],
            [kb.button("Бан / разбан", f"adm:ban:{user_id}", style="danger", icon="cancel")],
            [kb.button("Сбросить cooldown", f"adm:cool:{user_id}", style="primary", icon="refresh")],
            [kb.button("К пользователям", "adm:users:0", icon="back")],
        ]
        await safe_edit(callback, text, kb.keyboard(rows))
    except Exception as exc:
        await safe_edit(callback, f"Ошибка: {escape(services.error_text(exc))}", kb.admin_menu())
    await callback.answer()


@router.callback_query(F.data.startswith("adm:pro:"))
async def admin_pro(callback: CallbackQuery) -> None:
    if not await require_admin(callback):
        return
    _, _, user_id, days = callback.data.split(":")
    expires = await services.admin_grant_pro(int(user_id), int(days))
    await callback.answer("Готово.", show_alert=True)
    await safe_edit(callback, f"PRO обновлен. Действует до: {services.dt_text(expires)}.", kb.keyboard([[kb.button("Назад", f"adm:u:{user_id}", icon="back")]]))


@router.callback_query(F.data.startswith("adm:ban:"))
async def admin_ban(callback: CallbackQuery) -> None:
    admin = await require_admin(callback)
    if not admin:
        return
    target_id = int(callback.data.split(":")[2])
    try:
        state = await services.admin_toggle_ban(admin.telegram_id, target_id)
        await callback.answer("Статус обновлен.", show_alert=True)
        await safe_edit(callback, f"Блокировка: {'включена' if state else 'выключена'}.", kb.keyboard([[kb.button("Назад", f"adm:u:{target_id}", icon="back")]]))
    except Exception as exc:
        await callback.answer(services.error_text(exc), show_alert=True)


@router.callback_query(F.data.startswith("adm:cool:"))
async def admin_cooldown(callback: CallbackQuery) -> None:
    if not await require_admin(callback):
        return
    target_id = int(callback.data.split(":")[2])
    await services.admin_reset_cooldown(target_id)
    await callback.answer("Cooldown сброшен.", show_alert=True)
    await safe_edit(callback, "Cooldown ручного дайджеста сброшен.", kb.keyboard([[kb.button("Назад", f"adm:u:{target_id}", icon="back")]]))


@router.callback_query(F.data == "adm:promos")
async def admin_promos(callback: CallbackQuery) -> None:
    if not await require_admin(callback):
        return
    promos = await services.admin_promos()
    lines = ["<b>Промокоды</b>"]
    if promos:
        for promo in promos[:20]:
            lines.append(f"{escape(promo.code)} · {promo.duration_days} дн. · {promo.activations_count}/{promo.max_activations}")
    else:
        lines.append("Промокодов нет.")
    rows = [[kb.button("Создать промокод", "adm:promo_new", style="success", icon="add")]]
    for promo in promos[:10]:
        if len(promo.code) <= 40:
            rows.append([kb.button(f"Удалить {promo.code}", f"adm:promo_del:{promo.code}", style="danger", icon="delete")])
    rows.append([kb.button("В админку", "m:admin", icon="admin")])
    await safe_edit(callback, "\n".join(lines), kb.keyboard(rows))
    await callback.answer()


@router.callback_query(F.data == "adm:promo_new")
async def admin_promo_new(callback: CallbackQuery, state: FSMContext) -> None:
    if not await require_admin(callback):
        return
    await state.set_state(AdminPromoStates.waiting_code)
    await safe_edit(callback, "Отправьте код промокода.", kb.cancel_menu())
    await callback.answer()


@router.message(AdminPromoStates.waiting_code)
async def admin_promo_code(message: Message, state: FSMContext) -> None:
    user = await require_user_from_message(message)
    if not user or not services.is_admin(user):
        return
    await state.update_data(code=(message.text or "").strip())
    await state.set_state(AdminPromoStates.waiting_days)
    await message.answer("Сколько дней PRO выдавать?", reply_markup=kb.cancel_menu())


@router.message(AdminPromoStates.waiting_days)
async def admin_promo_days(message: Message, state: FSMContext) -> None:
    user = await require_user_from_message(message)
    if not user or not services.is_admin(user):
        return
    try:
        days = int((message.text or "").strip())
        if days <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите положительное число дней.", reply_markup=kb.cancel_menu())
        return
    await state.update_data(days=days)
    await state.set_state(AdminPromoStates.waiting_uses)
    await message.answer("Сколько активаций разрешить?", reply_markup=kb.cancel_menu())


@router.message(AdminPromoStates.waiting_uses)
async def admin_promo_uses(message: Message, state: FSMContext) -> None:
    user = await require_user_from_message(message)
    if not user or not services.is_admin(user):
        return
    try:
        uses = int((message.text or "").strip())
        if uses <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите положительное число активаций.", reply_markup=kb.cancel_menu())
        return
    data = await state.get_data()
    try:
        promo = await services.admin_create_promo(data["code"], int(data["days"]), uses)
        await state.clear()
        await message.answer(f"Промокод создан: {escape(promo.code)}.", reply_markup=kb.admin_menu())
    except Exception as exc:
        await message.answer(f"Не удалось создать промокод: {escape(services.error_text(exc))}", reply_markup=kb.admin_menu())


@router.callback_query(F.data.startswith("adm:promo_del:"))
async def admin_promo_delete(callback: CallbackQuery) -> None:
    if not await require_admin(callback):
        return
    code = callback.data.split(":", 2)[2]
    ok = await services.admin_delete_promo(code)
    promos = await services.admin_promos()
    lines = ["<b>Промокоды</b>", "Промокод удален." if ok else "Промокод не найден."]
    if promos:
        for promo in promos[:20]:
            lines.append(f"{escape(promo.code)} · {promo.duration_days} дн. · {promo.activations_count}/{promo.max_activations}")
    rows = [[kb.button("Создать промокод", "adm:promo_new", style="success", icon="add")], [kb.button("В админку", "m:admin", icon="admin")]]
    await safe_edit(callback, "\n".join(lines), kb.keyboard(rows))
    await callback.answer()


@router.callback_query(F.data == "adm:sessions")
async def admin_sessions(callback: CallbackQuery) -> None:
    if not await require_admin(callback):
        return
    sessions = await services.admin_sessions()
    lines = ["<b>Сессии парсера</b>"]
    if sessions:
        for session in sessions:
            lines.append(f"{escape(session.session_name)} · {escape(session.phone)} · {'активна' if session.is_active else 'выключена'}")
    else:
        lines.append("Сессий нет.")
    await safe_edit(callback, "\n".join(lines), kb.admin_menu())
    await callback.answer()


async def scheduler_loop(bot: Bot) -> None:
    await asyncio.sleep(10)
    last_expiry_date = None
    while True:
        try:
            now = datetime.utcnow()
            if now.minute == 0:
                await services.scheduled_digest_tick(bot)
            if now.hour == 10 and now.minute == 0 and last_expiry_date != now.date():
                await services.expiry_tick(bot)
                last_expiry_date = now.date()
            await asyncio.sleep(max(1, 60 - now.second))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Scheduler error: %s", exc)
            await asyncio.sleep(30)


async def health_server() -> None:
    config = uvicorn.Config(health_app, host="0.0.0.0", port=get_port(), log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def configure_bot(bot: Bot) -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_chat_menu_button(menu_button=MenuButtonDefault())
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Главное меню"),
            BotCommand(command="menu", description="Главное меню"),
            BotCommand(command="help", description="Помощь"),
        ]
    )


async def main() -> None:
    if not settings.telegram_bot_token or ":" not in settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing or invalid.")

    await services.init_storage()

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    await configure_bot(bot)

    tasks = [
        asyncio.create_task(start_parser(), name="parser"),
        asyncio.create_task(scheduler_loop(bot), name="scheduler"),
        asyncio.create_task(health_server(), name="health"),
    ]

    try:
        logger.info("Starting ZR4K plain bot polling.")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
