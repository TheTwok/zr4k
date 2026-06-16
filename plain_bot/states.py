from aiogram.fsm.state import State, StatesGroup


class SourceStates(StatesGroup):
    waiting_link = State()


class KeywordStates(StatesGroup):
    waiting_keyword = State()


class PromoStates(StatesGroup):
    waiting_code = State()


class ScheduleStates(StatesGroup):
    waiting_time = State()


class AdminPromoStates(StatesGroup):
    waiting_code = State()
    waiting_days = State()
    waiting_uses = State()
