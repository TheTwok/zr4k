import logging
import asyncio
import httpx
from collections import defaultdict
from groq import AsyncGroq, RateLimitError, APIError
from backend.app.config import settings
from backend.app.database import async_session
from backend.app.models import AIUsageStat

logger = logging.getLogger("zr4k.digest")

# System instruction for the Llama 3 model
SYSTEM_INSTRUCTION = (
    "Вы — профессиональный ИИ-ассистент ZR4K для анализа новостей и составления пересказов.\n"
    "Ваша задача — проанализировать сообщения из Telegram-каналов и выдать структурированный и связный рассказ (аналитическое саммари).\n\n"

    "ВЫ ДОЛЖНЫ ОТВЕЧАТЬ СТРОГО В УКАЗАННОМ ФОРМАТЕ. ЛЮБЫЕ ДРУГИЕ СЛОВА, ЗАГОЛОВКИ, ПРИВЕТСТВИЯ ИЛИ ВСТУПЛЕНИЯ КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНЫ.\n\n"

    "ПРАВИЛА ОФОРМЛЕНИЯ СТРОК:\n"
    "Каждая строка вашего ответа должна соответствовать формату:\n"
    "ИСТОЧНИК | КАТЕГОРИЯ | Текст связного рассказа\n\n"

    "Где:\n"
    "1. ИСТОЧНИК — точное название канала, взятое из входных данных (например, 'Lpr 1' или 'Varlamov News').\n"
    "2. КАТЕГОРИЯ — строго одна из списка разрешенных:\n"
    "   * ПОЛИТИКА\n"
    "   * ЭКОНОМИКА\n"
    "   * ТЕХНОЛОГИИ\n"
    "   * БЕЗОПАСНОСТЬ\n"
    "   * ПРОИСШЕСТВИЯ\n"
    "   * КУЛЬТУРА\n"
    "   * НАУКА\n"
    "   * ОБЩЕСТВО\n"
    "   Если новость трудно классифицировать, отнесите её к категории ОБЩЕСТВО.\n"
    "3. Текст связного рассказа — это краткое, ёмкое, изложенное по факту, обдуманное повествование в виде единого абзаца (рассказа) для каждой категории. Это должен быть именно рассказ/аналитический обзор, а не сухой прямой пересказ или перечисление отдельных новостей через запятую. Объедините все события из этого источника по данной категории в один связный и логичный текст, не упуская важных деталей и не нанося ущерб информативности.\n"
    "4. В тексте рассказа ЗАПРЕЩЕНО писать название источника или использовать Markdown-разметку (без **, ## и т.д.).\n"
    "5. СТРОГИЙ ЗАПРЕТ НА ВЫДУМЫВАНИЕ: Опирайтесь исключительно на факты из предоставленных сообщений.\n\n"

    "КРИТИЧЕСКИЕ ТРЕБОВАНИЯ К ТЕКСТУ РАССКАЗА:\n"
    "- Текст должен быть понятным, структурированным, логичным и аккуратно оформленным.\n"
    "- Текст не должен быть растянутым, пишите максимально емко и лаконично.\n"
    "- ПОЛНОЕ ОТСУТСТВИЕ ПОВТОРОВ: Категорически запрещено повторять одни и те же факты или информацию.\n"
    "- ПОЛНОЕ ОТСУТСТВИЕ «ВОДЫ» и лишних слов: Переходите сразу к сути новостей.\n\n"

    "ПРИМЕР:\n"
    "Входные сообщения:\n"
    "ИСТОЧНИК: Lpr 1\n"
    "СООБЩЕНИЯ:\n"
    "- В Краснодаре прошел сильный ливень, улицы затоплены.\n"
    "- Легкомоторный самолет жестко сел в Волгоградской области, пострадал пилот.\n\n"
    "ИСТОЧНИК: Varlamov News\n"
    "СООБЩЕНИЯ:\n"
    "- ЦРУ рассекретило архивные документы о НЛО в Венгрии в 1950-х годах.\n\n"

    "Результат:\n"
    "Lpr 1 | ПРОИСШЕСТВИЯ | В Краснодаре из-за обрушившегося сильного ливня оказались полностью затоплены городские улицы, в то время как в соседней Волгоградской области произошло крушение легкомоторного самолета, совершившего жесткую посадку, в результате которой пострадал пилот.\n"
    "Varlamov News | КУЛЬТУРА | Центральное разведывательное управление США открыло широкий доступ к своим архивным докладам за 1955 год, содержащим сведения о зафиксированных наблюдениях НЛО в воздушном пространстве между Будапештом и Москвой."
)

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
            {"role": "user", "content": f"Вот список сгруппированных по источникам сообщений:\n\n{combined_text}"}
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
                    {"text": f"Вот список сгруппированных по источникам сообщений:\n\n{combined_text}"}
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
            {"role": "user", "content": f"Вот список сгруппированных по источникам сообщений:\n\n{combined_text}"}
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

    # Parse and group the output structured text in Python to guarantee 100% correct layout
    lines = summary.split("\n")
    parsed_data = defaultdict(lambda: defaultdict(list))
    
    allowed_categories = {
        "ПОЛИТИКА", "ЭКОНОМИКА", "ТЕХНОЛОГИИ", "БЕЗОПАСНОСТЬ", 
        "СПОРТ", "ПРОИСШЕСТВИЯ", "КУЛЬТУРА", "НАУКА", "ОБЩЕСТВО"
    }
    
    for line in lines:
        line = line.strip()
        if not line or " | " not in line:
            continue
            
        parts = line.split(" | ", 2)
        if len(parts) < 3:
            continue
            
        channel = parts[0].strip()
        category = parts[1].strip().upper()
        text = parts[2].strip()
        
        # Strip potential lead bullets or formatting just in case
        if text.startswith("•") or text.startswith("-"):
            text = text[1:].strip()
            
        if not text:
            continue
            
        if category not in allowed_categories:
            # Try mapping common typos or fallback to ОБЩЕСТВО
            if "БЕЗОПАСН" in category:
                category = "БЕЗОПАСНОСТЬ"
            elif "ПОЛИТИК" in category:
                category = "ПОЛИТИКА"
            elif "ЭКОНОМИК" in category:
                category = "ЭКОНОМИКА"
            elif "ТЕХНОЛОГ" in category:
                category = "ТЕХНОЛОГИИ"
            elif "ПРОИСШЕСТВ" in category:
                category = "ПРОИСШЕСТВИЯ"
            elif "КУЛЬТУР" in category:
                category = "КУЛЬТУРА"
            elif "НАУК" in category or "НАУЧН" in category:
                category = "НАУКА"
            elif "СПОРТ" in category:
                category = "СПОРТ"
            else:
                category = "ОБЩЕСТВО"
                
        # Group under correct channel and category
        parsed_data[channel][category].append(text)

    if not parsed_data:
        # Fallback in case LLM completely failed format instructions
        return summary

    result_blocks = []
    for channel, categories in parsed_data.items():
        channel_block = []
        channel_block.append(channel.upper())
        channel_block.append("") # Empty line after channel title
        
        for category, items in categories.items():
            channel_block.append(category)
            joined_text = " ".join(items)
            channel_block.append(joined_text)
            channel_block.append("") # Empty line after category block
            
        block_text = "\n".join(channel_block).strip()
        if block_text:
            result_blocks.append(block_text)
            
    return "\n\n".join(result_blocks)
