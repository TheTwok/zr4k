from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


ICONS = {
    "overview": "6028435952299413210",
    "cabinet": "6028435952299413210",
    "sources": "6037475557082403885",
    "filters": "5904258298764334001",
    "digest": "5895519358871932592",
    "pro": "6028338546736107668",
    "crown": "6028338546736107668",
    "help": "6030848053177486888",
    "admin": "6030537007350944596",
    "add": "6032924188828767321",
    "list": "6034969813032374911",
    "delete": "6039522349517115015",
    "back": "6039539366177541657",
    "cancel": "6030757850274336631",
    "disable": "6039522349517115015",
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
    "done": "6030657343744644592",
    "select": "6037475557082403885",
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
        [button("Личный кабинет", "m:overview", style="primary", icon="cabinet")],
        [button("Источники", "m:sources", style="primary", icon="sources"), button("Фильтры", "m:filters", style="primary", icon="filters")],
        [button("Дайджест", "m:digest", style="primary", icon="digest"), button("Помощь", "m:help", style="primary", icon="help")],
    ]
    if is_admin:
        rows.append([button("Админ", "m:admin", style="primary", icon="admin")])
    return keyboard(rows)


def back_main() -> InlineKeyboardMarkup:
    return keyboard([[button("В главное меню", "m:main", icon="back")]])


def cabinet_menu(is_pro: bool, is_owner: bool = False) -> InlineKeyboardMarkup:
    rows = []
    if not is_owner:
        rows.append([button("Подписка PRO", "m:pro", style="success" if not is_pro else "primary", icon="pro")])
    rows.append([button("В главное меню", "m:main", icon="back")])
    return keyboard(rows)


def sources_menu() -> InlineKeyboardMarkup:
    return keyboard(
        [
            [button("Добавить источник", "src:add", style="success", icon="add")],
            [button("Перейти к фильтрам", "m:filters", style="primary", icon="filters")],
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


def digest_locked_menu() -> InlineKeyboardMarkup:
    return keyboard(
        [
            [button("Купить PRO", "pro:buy", style="success", icon="pay")],
            [button("Ввести промокод", "pro:promo", style="primary", icon="promo")],
            [button("В личный кабинет", "m:overview", icon="cabinet")],
        ]
    )


def schedule_menu() -> InlineKeyboardMarkup:
    return keyboard(
        [
            [button("Настроить ежедневный дайджест", "dig:sched", style="primary", icon="schedule")],
            [button("В раздел Дайджест", "m:digest", icon="digest")],
        ]
    )


def period_menu() -> InlineKeyboardMarkup:
    return keyboard(
        [
        [button("1 час", "dig:p:1", style="primary"), button("12 часов", "dig:p:12", style="primary")],
        [button("24 часа", "dig:p:24", style="primary"), button("48 часов", "dig:p:48", style="primary")],
        [button("7 дней", "dig:p:168", style="primary")],
        [button("Назад", "m:digest", icon="back")],
        ]
    )


def digest_source_menu(sources: list, selected_ids: set[int], can_generate: bool) -> InlineKeyboardMarkup:
    rows = []
    for source in sources:
        selected = source.id in selected_ids
        rows.append(
            [
                button(
                    f"{'Выбрано: ' if selected else ''}@{source.username}",
                    f"dig:src:{source.id}",
                    style="success" if selected else "primary",
                    icon="select",
                )
            ]
        )
    if can_generate:
        rows.append([button("Сгенерировать дайджест", "dig:run", style="success", icon="generate")])
    rows.append([button("Назад", "dig:g", icon="back")])
    return keyboard(rows)


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
            [button("PRO", "adm:users:pro:0", style="success", icon="crown"), button("FREE", "adm:users:free:0", style="primary", icon="users")],
            [button("Промокоды", "adm:promos", style="primary", icon="promo")],
            [button("Сессии парсера", "adm:sessions", style="primary", icon="sessions")],
            [button("В главное меню", "m:main", icon="back")],
        ]
    )


def cancel_menu() -> InlineKeyboardMarkup:
    return keyboard([[button("Отменить", "act:cancel", style="danger", icon="cancel")]])


def keyword_continue_menu(channel_id: int) -> InlineKeyboardMarkup:
    return keyboard(
        [
            [button("Готово", f"kw:done:{channel_id}", style="success", icon="done")],
            [button("Сменить тип фильтра", f"kw:add:{channel_id}", style="primary", icon="filters")],
        ]
    )
