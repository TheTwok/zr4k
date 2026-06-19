from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


ICONS = {
    "cabinet": "6032693626394382504",
    "sources": "5890883384057533697",
    "filters": "6034969813032374911",
    "digest": "5956148757899776734",
    "help": "6028435952299413210",
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


def source_button_text(source) -> str:
    return source.title or f"@{source.username}"


def main_menu(is_admin: bool = False, icons: dict[str, str] | None = None) -> InlineKeyboardMarkup:
    icons = icons or ICONS
    rows = [
        [button("Личный кабинет", "m:overview", style="success", icon=icons.get("cabinet"))],
        [
            button("Источники", "m:sources", style="primary", icon=icons.get("sources")),
            button("Фильтры", "m:filters", style="primary", icon=icons.get("filters")),
        ],
        [
            button("AI Дайджест", "m:digest", style="primary", icon=icons.get("digest")),
            button("FAQ", "m:help", style="primary", icon=icons.get("help")),
        ],
    ]
    if is_admin:
        rows.append([button("Админ", "m:admin", style="primary")])
    return keyboard(rows)


def back_main() -> InlineKeyboardMarkup:
    return keyboard([[button("В главное меню", "m:main")]])


def cabinet_menu(is_pro: bool, is_owner: bool = False) -> InlineKeyboardMarkup:
    rows = []
    if not is_owner:
        if is_pro:
            rows.append([button("Продлить подписку", "pro:buy", style="success")])
        else:
            rows.append([button("Подписка PRO", "m:pro", style="success")])
    rows.append([button("В главное меню", "m:main")])
    return keyboard(rows)


def sources_menu() -> InlineKeyboardMarkup:
    return keyboard(
        [
            [button("Добавить источник", "src:add", style="success")],
            [button("Перейти к фильтрам", "m:filters", style="primary")],
            [button("Удалить источник", "src:del", style="danger")],
            [button("В главное меню", "m:main")],
        ]
    )


def digest_menu(is_pro: bool) -> InlineKeyboardMarkup:
    rows = [
        [button("Расписание", "dig:sched", style="primary")],
        [button("В главное меню", "m:main")],
    ]
    if is_pro:
        rows.insert(0, [button("Составить дайджест", "dig:g", style="success")])
    return keyboard(rows)


def digest_sources_menu(sources: list) -> InlineKeyboardMarkup:
    rows = [[button(source_button_text(source), f"dig:source:{source.id}", style="primary")] for source in sources]
    rows.append([button("В главное меню", "m:main")])
    return keyboard(rows)


def digest_source_actions(channel_id: int) -> InlineKeyboardMarkup:
    return keyboard(
        [
            [button("Составить дайджест", f"dig:g:{channel_id}", style="success")],
            [button("Расписание", f"sch:c:{channel_id}", style="primary")],
            [button("К источникам", "m:digest")],
        ]
    )


def digest_locked_menu() -> InlineKeyboardMarkup:
    return keyboard(
        [
            [button("Купить PRO", "pro:buy", style="success")],
            [button("Ввести промокод", "pro:promo", style="primary")],
            [button("В главное меню", "m:main")],
        ]
    )


def schedule_menu() -> InlineKeyboardMarkup:
    return keyboard(
        [
            [button("Настроить ежедневный AI Дайджест", "dig:sched", style="primary")],
            [button("В раздел AI Дайджест", "m:digest")],
        ]
    )


def period_menu() -> InlineKeyboardMarkup:
    return keyboard(
        [
        [button("1 час", "dig:p:1", style="primary"), button("3 часа", "dig:p:3", style="primary")],
        [button("6 часов", "dig:p:6", style="primary"), button("12 часов", "dig:p:12", style="primary")],
        [button("Назад", "m:digest")],
        ]
    )


def digest_source_menu(sources: list, selected_ids: set[int], can_generate: bool) -> InlineKeyboardMarkup:
    rows = []
    for source in sources:
        selected = source.id in selected_ids
        rows.append(
            [
                button(
                    f"{'Выбрано: ' if selected else ''}{source_button_text(source)}",
                    f"dig:src:{source.id}",
                    style="success" if selected else "primary",
                )
            ]
        )
    if can_generate:
        rows.append([button("Составить дайджест", "dig:run", style="success")])
    rows.append([button("Назад", "dig:g")])
    return keyboard(rows)


def pro_menu(is_pro: bool, price: int = 50) -> InlineKeyboardMarkup:
    rows = [
        [button("Активировать промокод", "pro:promo", style="primary")],
        [button("В главное меню", "m:main")],
    ]
    if not is_pro:
        rows.insert(0, [button(f"Оплатить {price} Stars", "pro:buy", style="success")])
    return keyboard(rows)


def admin_menu() -> InlineKeyboardMarkup:
    return keyboard(
        [
            [button("Статистика", "adm:stats", style="primary")],
            [button("PRO", "adm:users:pro:0", style="success"), button("FREE", "adm:users:free:0", style="primary")],
            [button("Промокоды", "adm:promos", style="primary")],
            [button("Тексты меню", "adm:texts", style="primary")],
            [button("Настройки", "adm:settings", style="primary")],
            [button("Сессии парсера", "adm:sessions", style="primary")],
            [button("В главное меню", "m:main")],
        ]
    )


def cancel_menu() -> InlineKeyboardMarkup:
    return keyboard([[button("Отменить", "act:cancel", style="danger")]])


def keyword_continue_menu(channel_id: int) -> InlineKeyboardMarkup:
    return keyboard(
        [
            [button("Сменить режим", f"kw:add:{channel_id}", style="primary")],
            [button("Назад к фильтрам", f"kw:done:{channel_id}")],
        ]
    )
