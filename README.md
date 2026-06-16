# ZR4K

ZR4K is now deployed as a plain Telegram bot without a Mini App.

The bot keeps the existing product features:

- public Telegram channel sources;
- keyword and phrase filters;
- matched posts sent directly into the bot chat;
- manual AI digests sent into the chat;
- scheduled AI digests sent into the chat;
- Telegram Stars payment for PRO;
- promo code activation;
- admin stats, users, promocodes, parser sessions;
- Telethon userbot parser for source monitoring.

## Runtime

Bothost should build the root `Dockerfile`.

The container starts:

```bash
python -m plain_bot.main
```

The same process runs:

- aiogram polling bot;
- Telethon parser;
- digest scheduler;
- small HTTP health server on `PORT` or compatible Bothost port variables.

## Required environment variables

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`
- `ADMIN_USER_ID`
- at least one digest provider key: `GROQ_API_KEY`, `MISTRAL_API_KEY`, or `GEMINI_API_KEY`

No `APP_URL`, public HTTPS certificate, frontend build, or Telegram Mini App configuration is required.

## Local checks

```bash
backend\.venv\Scripts\python.exe -c "import plain_bot.main"
backend\.venv\Scripts\python.exe -m pytest backend\tests
```
