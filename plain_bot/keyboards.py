from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


ICONS = {
    "overview": "6028435952299413210",
    "sources": "6037475557082403885",
    "filters": "5904258298764334001",
    "digest": "5895519358871932592",
    "pro": "6028338546736107668",
    "help": "6030848053177486888",
    "admin": "6030537007350944596",
    "add": "6032924188828767321",
    "list": "6034969813032374911",
    "delete": "6039522349517115015",
    "back": "6039539366177541657",
    "cancel": "6030757850274336631",
    "pay": "6028338546736107668",
    "promo": "5773677501825945508",
    "schedule": "6039569594157371705",
    "generate": "5774022692642492953",
    "settings": "5904258298764334001",
    "stats": "5877485980901971030",
    "users": "5879770735999717115",
    "sessions": "6037249452824072506",
    "next": "5895383238473421210",
    "refresh": "6030657343744644592",
}


def button(
    text: str,
    callback_data: str | None = None,
    url: str | None = None,
    style: str | None = None,
    icon: str | None = None,
) -> InlineKeyboardButton:
    kwargs = {"text": text, "callback_data": callback_data, "url": url}
    if style:
        kwargs["style"] = style
    if icon:
        kwargs["icon_custom_emoji_id"] = ICONS.get(icon, icon)
    return InlineKeyboardButton(**kwargs)


def keyboard(rows: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


def main_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [button("Обзор", "m:overview", icon="overview"), button("Источники", "m:sources", style="primary", icon="sources")],
        [button("Фильтры", "m:filters", style="primary", icon="filters"), button("Дайджест", "m:digest", style="primary", icon="digest")],
        [button("PRO", "m:pro", style="success", icon="pro")],
        [button("Помощь", "m:help", icon="help")],
    ]
    if is_admin:
        rows.insert(-1, [button("Админ", "m:admin", style="primary", icon="admin")])
    return keyboard(rows)


def back_main() -> InlineKeyboardMarkup:
    return keyboard([[button("В главное меню", "m:main", icon="back")]])


def sources_menu() -> InlineKeyboardMarkup:
    return keyboard(
        [
            [button("Добавить источник", "src:add", style="success", icon="add")],
            [button("Список источников", "src:list", style="primary", icon="list")],
            [button("Удалить источник", "src:del", style="danger", icon="delete")],
            [button("В главное меню", "m:main", icon="back")],
        ]
    )


def digest_menu(is_pro: bool) -> InlineKeyboardMarkup:
    rows = [
        [button("Расписание", "dig:sched", style="primary", icon="schedule")],
        [button("В главное меню", "m:main", icon="back")],
    ]
    if is_pro:
        rows.insert(0, [button("Сгенерировать сейчас", "dig:g", style="success", icon="generate")])
    return keyboard(rows)


def period_menu() -> InlineKeyboardMarkup:
    return keyboard(
        [
        [button("1 час", "dig:p:1", style="primary"), button("12 часов", "dig:p:12", style="primary")],
        [button("24 часа", "dig:p:24", style="primary"), button("48 часов", "dig:p:48", style="primary")],
        [button("7 дней", "dig:p:168", style="primary")],
        [button("Назад", "m:digest", icon="back")],
        ]
    )


def pro_menu(is_pro: bool) -> InlineKeyboardMarkup:
    rows = [
        [button("Активировать промокод", "pro:promo", style="primary", icon="promo")],
        [button("В главное меню", "m:main", icon="back")],
    ]
    if not is_pro:
        rows.insert(0, [button("Оплатить 50 Stars", "pro:buy", style="success", icon="pay")])
    return keyboard(rows)


def admin_menu() -> InlineKeyboardMarkup:
    return keyboard(
        [
            [button("Статистика", "adm:stats", style="primary", icon="stats")],
            [button("Пользователи", "adm:users:0", style="primary", icon="users")],
            [button("Промокоды", "adm:promos", style="primary", icon="promo")],
            [button("Сессии парсера", "adm:sessions", style="primary", icon="sessions")],
            [button("В главное меню", "m:main", icon="back")],
        ]
    )


def cancel_menu() -> InlineKeyboardMarkup:
    return keyboard([[button("Отменить", "act:cancel", style="danger", icon="cancel")]])
