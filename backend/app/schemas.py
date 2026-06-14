import re
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict

def extract_clean_username(value: str) -> str:
    val = value.strip()
    
    # Check for invite links (joinchat or + links)
    if "/joinchat/" in val or "t.me/+" in val or "/+" in val or "joinchat" in val:
        raise ValueError("Канал должен быть открытым. Ссылки-приглашения не поддерживаются.")
        
    # Match standard t.me links or raw @username
    pattern = r"^(?:https?://)?(?:t\.me|telegram\.me|telegram\.dog)/?@?([a-zA-Z0-9_]{4,32})/?$"
    match = re.match(pattern, val, re.IGNORECASE)
    if match:
        return match.group(1).lower()
        
    pattern_raw = r"^@?([a-zA-Z0-9_]{4,32})$"
    match_raw = re.match(pattern_raw, val)
    if match_raw:
        return match_raw.group(1).lower()
        
    raise ValueError("Неверный формат. Используйте @username или t.me/username.")

class UserSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    telegram_id: int
    username: str | None
    language_code: str
    pro_expires_at: datetime | None = None
    is_pro: bool
    is_admin: bool
    last_digest_at: datetime | None = None

class ChannelSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    title: str | None
    digest_schedule_time: str | None = None
    digest_schedule_days: str | None = None

class SourceCreate(BaseModel):
    link: str

    @field_validator("link")
    @classmethod
    def validate_link(cls, v: str) -> str:
        return extract_clean_username(v)

class KeywordSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    channel_id: int
    keyword: str
    mode: str

class KeywordCreate(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=100)
    mode: str = Field(default="semantic") # semantic, exact_phrase, exact_word, exclude

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        if v not in ("semantic", "exact_phrase", "exact_word", "exclude"):
            raise ValueError("Invalid keyword mode.")
        return v

class CaughtMessageSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    channel_id: int
    channel_username: str
    channel_title: str | None
    message_id: int
    text: str
    url: str
    created_at: datetime

class PromoCodeActivate(BaseModel):
    code: str = Field(..., min_length=1)

class PromoCodeCreate(BaseModel):
    code: str = Field(..., min_length=3)
    duration_days: int = Field(default=30)
    max_activations: int = Field(default=1)

class ScheduleUpdate(BaseModel):
    time: str | None = Field(None, description="Time in HH:00 format, or None to disable")

class ChannelScheduleUpdate(BaseModel):
    time: str | None = Field(None, description="Time in HH:00 format, or None to disable")
    days: str | None = Field(None, description="Comma-separated days of the week, e.g. 'ПН,ВТ,СР'")

class DigestRequest(BaseModel):
    channel_ids: list[int] = Field(default_factory=list) # empty means all channels
    period_hours: int = Field(default=24) # 12, 24, 48, 168 (1 week)
    use_keywords_only: bool = Field(default=True)
