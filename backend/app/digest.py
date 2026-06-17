import logging
import httpx
from collections import defaultdict
from groq import AsyncGroq
from backend.app.config import settings
from backend.app.database import async_session
from backend.app.models import AIUsageStat
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("zr4k.digest")

SYSTEM_INSTRUCTION = """Ты — опытный аналитик данных и главный технический редактор. Твоя задача — проанализировать хронологическую ленту сообщений из Telegram и составить из них один качественный, осмысленный и структурированный дайджест.

Работай строго по следующим правилам:

1. ОГРАНИЧЕНИЕ ПО ДЛИНЕ (КРИТИЧЕСКИ ВАЖНО)
- Максимальная длина твоего ответа строго ограничена: до 3000-3500 символов с учетом пробелов. Превышать этот лимит категорически запрещено, иначе сообщение не поместится в Telegram.
- Будь максимально лаконичен. Безжалостно вырезай повторы мыслей, дублирующуюся информацию и «воду». Излагай факты плотно.

2. СТИЛЬ И ЯЗЫК
- Пиши на русском языке — простым, живым, естественным и легко читаемым человеком языком.
- КАТЕГОРИЧЕСКИ ЗАПРЕЩЕН ИИ-стиль, канцелярит, неестественные обороты («в данном контексте», «важно отметить», «исходя из вышесказанного») и шаблонные фразы.
- ЗАПРЕЩЕН маркетинговый мусор и избитые метафоры (слова вроде «революционный», «уникальный», «невероятный», «экосистема», «прорыв»).
- Фокусируйся на конкретике вместо абстракций. Используй точные цифры, даты, имена, названия и ссылки, если они есть в исходных сообщениях.

3. ФАКТИЧЕСКАЯ ТОЧНОСТЬ (НУЛЕВАЯ ТОЛЕРАНТНОСТЬ К ВЫМЫСЛУ)
- Опирайся исключительно на предоставленный текст сообщений. Тебе запрещено галлюцинировать, додумывать детали, делать предположения, интерпретировать скрытый смысл или предсказывать последствия событий.
- Если в сообщениях нет четких фактов по какой-то теме, ты просто её не упоминаешь. Никакой отсебятины.

4. СТРУКТУРА И ФОРМАТИРОВАНИЕ
- ЗАПРЕЩЕНЫ любые бессмысленные вступления, искусственная вежливость и приветствия (например, «Вот ваш дайджест за сегодня:», «Привет! Я проанализировал чат...»). Начинай сразу с сути.
- ЗАПРЕЩЕНЫ резюме, общие выводы и напутствия в конце текста (например, «Будем следить за развитием событий...»). Текст должен заканчиваться последним полезным фактом.
- Начни дайджест с сильного, емкого захода — одним коротким абзацем выдели главный инфоповод, тренд или самую важную новость за этот период.
- Раздели массив информации на 2–4 логических блока в зависимости от тематики сообщений. Дай каждому блоку четкий и понятный заголовок через маркер «### Заголовок».
- Внутри блоков используй короткие абзацы и структурированные списки. Выделяй ключевые фразы, цифры или триггеры жирным шрифтом (**текст**), чтобы облегчить сканирование текста глазами.

Исходные сообщения для анализа передаются ниже. Сделай из них идеальную выжимку."""

async def log_ai_usage(provider: str, prompt_tokens: int, completion_tokens: int, total_tokens: int, is_success: bool, error_message: str | None = None, db: AsyncSession = None):
    try:
        stat = AIUsageStat(
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            is_success=is_success,
            error_message=error_message[:500] if error_message else None
        )
        if db:
            db.add(stat)
            await db.commit()
        else:
            async with async_session() as session:
                session.add(stat)
                await session.commit()
    except Exception as e:
        logger.error(f"Failed to save AI usage statistics to DB: {e}")

async def call_groq(combined_text: str) -> tuple[str, int, int]:
    client = AsyncGroq(api_key=settings.groq_api_key)
    chat_completion = await client.chat.completions.create(
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": f"Исходные сообщения для анализа:\n\n{combined_text}"}
        ],
        model="llama-3.1-8b-instant",
        temperature=0.3,
    )
    content = chat_completion.choices[0].message.content
    usage = chat_completion.usage
    return content, usage.prompt_tokens, usage.completion_tokens

async def call_gemini(combined_text: str) -> tuple[str, int, int]:
    api_key = settings.gemini_api_key
    headers = {"Content-Type": "application/json"}
    
    # AQ. is the new Google API key format — use ?key= query parameter.
    # ya29. is an OAuth2 access token — use Authorization: Bearer header.
    if api_key.startswith("ya29."):
        headers["Authorization"] = f"Bearer {api_key}"
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    else:
        # Standard API key (AIza..., AQ., etc.) — always use ?key=
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"Исходные сообщения для анализа:\n\n{combined_text}"}
                ]
            }
        ],
        "systemInstruction": {
            "parts": [
                {"text": SYSTEM_INSTRUCTION}
            ]
        },
        "generationConfig": {
            "temperature": 0.3
        }
    }
    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        content = data["candidates"][0]["content"]["parts"][0]["text"]
        metadata = data.get("usageMetadata", {})
        prompt_tokens = metadata.get("promptTokenCount", 0)
        completion_tokens = metadata.get("candidatesTokenCount", 0)
        return content, prompt_tokens, completion_tokens

async def call_mistral(combined_text: str) -> tuple[str, int, int]:
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.mistral_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "mistral-small-latest",
        "messages": [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": f"Исходные сообщения для анализа:\n\n{combined_text}"}
        ],
        "temperature": 0.3
    }
    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        return content, prompt_tokens, completion_tokens

async def generate_summary(messages_texts: list[dict | str], db: AsyncSession = None) -> str:
    """
    Generates a digest summary from message texts using an AI provider cascade (Groq -> Gemini -> Mistral).
    Hides raw exceptions from users and logs detailed token/error statistics.
    """
    if not messages_texts:
        return "Нет новых сообщений для составления дайджеста."

    # Group messages by channel
    grouped_by_channel = defaultdict(list)
    for item in messages_texts:
        if isinstance(item, dict):
            channel_name = item.get("channel") or "Неизвестный источник"
            text = item.get("text", "").strip()
            if text:
                grouped_by_channel[channel_name].append(text)
        else:
            text = str(item).strip()
            if text:
                grouped_by_channel["Неизвестный источник"].append(text)

    if not grouped_by_channel:
        return "Нет новых сообщений для составления дайджеста."

    formatted_payload = []
    for channel, texts in grouped_by_channel.items():
        formatted_payload.append(f"ИСТОЧНИК: {channel}\nСООБЩЕНИЯ:\n" + "\n".join(f"- {t}" for t in texts))

    combined_text = "\n\n===\n\n".join(formatted_payload)
    
    # Cascade calls: Groq -> Gemini -> Mistral
    summary = None
    providers_to_try = []
    
    # Only try Groq if key is set and not default placeholder, and text size is reasonably small
    # (Groq Free Tier TPM limit is 6000, roughly 20k characters including response)
    if settings.groq_api_key and settings.groq_api_key != "YOUR_GROQ_API_KEY_HERE" and len(combined_text) < 18000:
        providers_to_try.append(("groq", call_groq))
    else:
        logger.info("Skipping Groq: payload too large or API key is not configured.")
        
    providers_to_try.append(("gemini", call_gemini))
    providers_to_try.append(("mistral", call_mistral))
    
    last_error_msg = ""
    
    for provider_name, call_fn in providers_to_try:
        try:
            logger.info(f"Attempting digest generation using: {provider_name}...")
            content, prompt_tokens, completion_tokens = await call_fn(combined_text)
            
            if content and content.strip():
                summary = content
                # Log successful usage
                await log_ai_usage(
                    provider=provider_name,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    is_success=True,
                    db=db
                )
                logger.info(f"Successfully generated digest via {provider_name} ({prompt_tokens + completion_tokens} tokens).")
                break
        except Exception as e:
            err_msg = str(e)
            logger.warning(f"AI provider {provider_name} failed: {err_msg}")
            last_error_msg = err_msg
            # Log failed usage
            await log_ai_usage(
                provider=provider_name,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                is_success=False,
                error_message=err_msg,
                db=db
            )

    if not summary:
        logger.error(f"All AI providers failed. Last error: {last_error_msg}")
        return "Не удалось сгенерировать дайджест. ИИ-ассистент временно перегружен или недоступен. Пожалуйста, попробуйте повторить попытку позже."

    return summary.strip()
