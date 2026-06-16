# ZR4K plain Telegram bot

This folder contains the non-Mini-App Telegram interface.

It keeps the existing backend storage and domain logic:

- source management;
- keyword filters;
- manual and scheduled AI digests sent directly to chat;
- promo codes;
- Telegram Stars payment for PRO;
- admin stats, users, promos, parser sessions;
- parser startup in the same process.

## Menu structure

The bot uses ordinary Telegram inline buttons:

- Main menu
- Overview
- Sources
- Filters
- Digest
- PRO
- Admin
- Help

Button styling uses Telegram Bot API `style` values:

- `success` for positive actions;
- `primary` for main navigation and settings;
- `danger` for destructive actions.

Button icons use `icon_custom_emoji_id` from `tgiosicons` and `TgAndroidIcons`. These are monochrome Telegram custom emoji icons, not ordinary colored emoji.

## Bothost

The root `Dockerfile` starts this plain bot:

```bash
python -m plain_bot.main
```

The process also starts a small HTTP health server on `PORT`, `APP_PORT`, `WEB_PORT`, or `BOTHOST_PORT` so a web-oriented host can keep the container alive.

Required environment variables:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`
- `ADMIN_USER_ID`
- `GROQ_API_KEY`, `MISTRAL_API_KEY`, or `GEMINI_API_KEY` for digests

No public HTTPS Mini App URL or certificate is required in this mode.
